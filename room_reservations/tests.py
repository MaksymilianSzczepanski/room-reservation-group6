from datetime import datetime, time, timedelta

from django.core import mail
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .admin import RoomGuardianAdminForm
from . import STATUS_APPROVED, STATUS_CANCELLED, STATUS_PENDING, STATUS_REJECTED
from .models import Attribute, Reservation, Room, RoomGuardian, get_reservation_hours_error
from .permissions import can_create_reservations
from .views import get_guardian_pending_count


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="test@example.com",
)
class ReservationPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client = APIClient()
        self.url = reverse("reservations-list")
        self.room = Room.objects.create(name="Aula 101", building="A", capacity=30)

        self.student = User.objects.create_user(username="student", password="test")
        students_group, _ = Group.objects.get_or_create(name="Students")
        self.student.groups.add(students_group)

        self.employee = User.objects.create_user(
            username="employee",
            password="test",
            email="employee@example.com",
        )
        self.guardian = User.objects.create_user(
            username="guardian",
            password="test",
            email="guardian@example.com",
        )
        RoomGuardian.objects.create(user=self.guardian, room=self.room)

    def reservation_payload(self, days_from_now=1):
        start = self.make_local_datetime(days_from_now=days_from_now, hour=9)
        end = start + timedelta(hours=1)
        return {
            "room": self.room.id,
            "title": "Spotkanie projektowe",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "note": "",
        }

    def test_student_can_view_reservations(self):
        self.client.force_authenticate(self.student)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_student_cannot_create_reservation(self):
        self.client.force_authenticate(self.student)

        response = self.client.post(self.url, self.reservation_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_student_can_create_reservation(self):
        self.client.force_authenticate(self.employee)

        response = self.client.post(self.url, self.reservation_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_new_reservation_sends_email_to_guardian(self):
        self.client.force_authenticate(self.employee)

        response = self.client.post(self.url, self.reservation_payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["guardian@example.com"])
        self.assertIn("Nowa prosba o rezerwacje", mail.outbox[0].subject)

    def test_approval_sends_email_to_requester(self):
        reservation = self.create_pending_reservation()
        self.client.force_login(self.guardian)

        response = self.client.post(
            reverse("guardian_reservation_decision", args=[reservation.id]),
            {"decision": STATUS_APPROVED, "next": reverse("guardian_dashboard")},
        )

        reservation.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(reservation.status, STATUS_APPROVED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["employee@example.com"])
        self.assertIn("zaakceptowana", mail.outbox[0].body)

    def test_rejection_requires_comment(self):
        reservation = self.create_pending_reservation()
        self.client.force_login(self.guardian)

        response = self.client.post(
            reverse("guardian_reservation_decision", args=[reservation.id]),
            {"decision": STATUS_REJECTED, "next": reverse("guardian_dashboard")},
        )

        reservation.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(reservation.status, STATUS_PENDING)
        self.assertEqual(len(mail.outbox), 0)

    def test_rejection_sends_comment_to_requester(self):
        reservation = self.create_pending_reservation()
        self.client.force_login(self.guardian)
        comment = "Sala jest potrzebna na egzamin."

        response = self.client.post(
            reverse("guardian_reservation_decision", args=[reservation.id]),
            {
                "decision": STATUS_REJECTED,
                "decision_comment": comment,
                "next": reverse("guardian_dashboard"),
            },
        )

        reservation.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(reservation.status, STATUS_REJECTED)
        self.assertEqual(reservation.decision_comment, comment)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["employee@example.com"])
        self.assertIn(comment, mail.outbox[0].body)

    def test_reservation_cannot_start_before_7(self):
        self.client.force_authenticate(self.employee)
        payload = self.reservation_payload()
        payload["start"] = self.make_local_datetime(days_from_now=2, hour=6, minute=30).isoformat()
        payload["end"] = self.make_local_datetime(days_from_now=2, hour=8).isoformat()

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("07:00-22:00", str(response.data))

    def test_reservation_cannot_end_after_22(self):
        self.client.force_authenticate(self.employee)
        payload = self.reservation_payload()
        payload["start"] = self.make_local_datetime(days_from_now=2, hour=21).isoformat()
        payload["end"] = self.make_local_datetime(days_from_now=2, hour=22, minute=30).isoformat()

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("07:00-22:00", str(response.data))

    def test_reservation_can_use_boundary_hours(self):
        self.client.force_authenticate(self.employee)
        payload = self.reservation_payload()
        payload["start"] = self.make_local_datetime(days_from_now=2, hour=7).isoformat()
        payload["end"] = self.make_local_datetime(days_from_now=2, hour=22).isoformat()

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def create_pending_reservation(self):
        start = self.make_local_datetime(days_from_now=3, hour=10)
        return Reservation.objects.create(
            room=self.room,
            user=self.employee,
            title="Konsultacje",
            start=start,
            end=start + timedelta(hours=1),
            status=STATUS_PENDING,
        )

    def make_local_datetime(self, days_from_now, hour, minute=0):
        current_tz = timezone.get_current_timezone()
        target_date = timezone.localdate() + timedelta(days=days_from_now)
        naive_value = datetime.combine(target_date, time(hour=hour, minute=minute))
        return timezone.make_aware(naive_value, current_tz)


class RoomSearchAttributeFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("rooms-list")

        self.wifi = Attribute.objects.create(name="Dostep wifi")
        self.camera = Attribute.objects.create(name="Kamera")
        self.projector = Attribute.objects.create(name="Projektor")

        self.room_with_both = Room.objects.create(name="Sala A", building="A", capacity=20)
        self.room_with_both.attributes.set([self.wifi, self.camera])

        self.room_with_one = Room.objects.create(name="Sala B", building="A", capacity=20)
        self.room_with_one.attributes.set([self.wifi])

        self.room_with_other_pair = Room.objects.create(name="Sala C", building="A", capacity=20)
        self.room_with_other_pair.attributes.set([self.camera, self.projector])

    def test_search_with_multiple_attributes_requires_all_of_them(self):
        response = self.client.get(
            self.url,
            {"attributes__id": [self.wifi.id, self.camera.id]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        rooms = data if isinstance(data, list) else data.get("results", [])

        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0]["id"], self.room_with_both.id)


class RoomGuardianAdminFormTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="opiekun-admin", password="test")
        self.room_one = Room.objects.create(name="Sala Admin 1", building="A", capacity=10)
        self.room_two = Room.objects.create(name="Sala Admin 2", building="B", capacity=12)

    def test_admin_form_allows_selecting_multiple_rooms(self):
        form = RoomGuardianAdminForm(
            data={
                "user": self.user.id,
                "rooms": [self.room_one.id, self.room_two.id],
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_admin_form_blocks_duplicate_room_assignment(self):
        RoomGuardian.objects.create(user=self.user, room=self.room_one)

        form = RoomGuardianAdminForm(
            data={
                "user": self.user.id,
                "rooms": [self.room_one.id, self.room_two.id],
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("juz przypisane sale", str(form.errors))


class ReservationHoursHelperTests(TestCase):
    def test_returns_none_when_start_or_end_is_missing(self):
        self.assertIsNone(get_reservation_hours_error(None, None))

    def test_rejects_reservation_crossing_midnight(self):
        start = self.make_local_datetime(days_from_now=1, hour=21)
        end = start + timedelta(hours=4)

        error = get_reservation_hours_error(start, end)

        self.assertIn("jednym dniu", error)

    def make_local_datetime(self, days_from_now, hour, minute=0):
        current_tz = timezone.get_current_timezone()
        target_date = timezone.localdate() + timedelta(days=days_from_now)
        naive_value = datetime.combine(target_date, time(hour=hour, minute=minute))
        return timezone.make_aware(naive_value, current_tz)


class ReservationModelValidationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="employee-model", password="test")
        self.room = Room.objects.create(name="Sala Model", building="A", capacity=25)

    def test_cancelled_reservation_does_not_block_new_one(self):
        start = self.make_local_datetime(days_from_now=2, hour=10)
        Reservation.objects.create(
            room=self.room,
            user=self.user,
            title="Anulowana",
            start=start,
            end=start + timedelta(hours=1),
            status=STATUS_CANCELLED,
        )

        reservation = Reservation(
            room=self.room,
            user=self.user,
            title="Nowa",
            start=start,
            end=start + timedelta(hours=1),
        )

        reservation.full_clean()

    def test_pending_reservation_blocks_overlapping_new_one(self):
        start = self.make_local_datetime(days_from_now=2, hour=12)
        Reservation.objects.create(
            room=self.room,
            user=self.user,
            title="Istniejaca",
            start=start,
            end=start + timedelta(hours=2),
            status=STATUS_PENDING,
        )

        reservation = Reservation(
            room=self.room,
            user=self.user,
            title="Nakladajaca",
            start=start + timedelta(minutes=30),
            end=start + timedelta(hours=1, minutes=30),
        )

        with self.assertRaisesMessage(ValidationError, "already reserved"):
            reservation.full_clean()

    def make_local_datetime(self, days_from_now, hour, minute=0):
        current_tz = timezone.get_current_timezone()
        target_date = timezone.localdate() + timedelta(days=days_from_now)
        naive_value = datetime.combine(target_date, time(hour=hour, minute=minute))
        return timezone.make_aware(naive_value, current_tz)


class ReservationPermissionHelperTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.student = User.objects.create_user(username="student-helper", password="test")
        self.employee = User.objects.create_user(username="employee-helper", password="test")
        students_group, _ = Group.objects.get_or_create(name="Students")
        self.student.groups.add(students_group)

    def test_anonymous_user_cannot_create_reservations(self):
        self.assertFalse(can_create_reservations(AnonymousUser()))

    def test_student_cannot_create_reservations(self):
        self.assertFalse(can_create_reservations(self.student))

    def test_non_student_can_create_reservations(self):
        self.assertTrue(can_create_reservations(self.employee))


class SearchAndLoginFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client = APIClient()
        self.search_url = reverse("search")
        self.login_url = reverse("modal_login")
        self.calendar_url = reverse("calendar")
        self.user = User.objects.create_user(
            username="login-user",
            password="secret123",
        )

    def test_search_view_preserves_safe_next_target_for_guest(self):
        response = self.client.get(self.search_url, {"next": self.calendar_url})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.context["next_target"], self.calendar_url)
        self.assertTrue(response.context["show_login_modal"])

    def test_search_view_rejects_external_next_target(self):
        response = self.client.get(self.search_url, {"next": "https://evil.example.com"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.context["next_target"], self.search_url)
        self.assertFalse(response.context["show_login_modal"])

    def test_modal_login_redirects_back_to_safe_next_url(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": "secret123",
                "next": self.calendar_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.calendar_url)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.id))

    def test_modal_login_rejects_external_redirect_target(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": "secret123",
                "next": "https://evil.example.com",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.search_url)

    def test_modal_login_stores_error_state_after_failed_login(self):
        response = self.client.post(
            self.login_url,
            {
                "username": self.user.username,
                "password": "wrong-password",
                "next": self.calendar_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("next=%2Fcalendar%2F", response.url)
        self.assertTrue(self.client.session["show_login_modal"])
        self.assertEqual(
            self.client.session["login_error"],
            "Nieprawidlowy login lub haslo.",
        )


class GuardianPendingCountTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.guardian = User.objects.create_user(username="guardian-count", password="test")
        self.employee = User.objects.create_user(username="employee-count", password="test")
        self.room = Room.objects.create(name="Sala Guardian", building="B", capacity=40)
        RoomGuardian.objects.create(user=self.guardian, room=self.room)

    def test_counts_only_pending_reservations_for_guarded_rooms(self):
        start = self.make_local_datetime(days_from_now=1, hour=8)
        Reservation.objects.create(
            room=self.room,
            user=self.employee,
            title="Pending 1",
            start=start,
            end=start + timedelta(hours=1),
            status=STATUS_PENDING,
        )
        Reservation.objects.create(
            room=self.room,
            user=self.employee,
            title="Approved",
            start=start + timedelta(hours=2),
            end=start + timedelta(hours=3),
            status=STATUS_APPROVED,
        )

        self.assertEqual(get_guardian_pending_count(self.guardian), 1)
        self.assertEqual(get_guardian_pending_count(AnonymousUser()), 0)

    def make_local_datetime(self, days_from_now, hour, minute=0):
        current_tz = timezone.get_current_timezone()
        target_date = timezone.localdate() + timedelta(days=days_from_now)
        naive_value = datetime.combine(target_date, time(hour=hour, minute=minute))
        return timezone.make_aware(naive_value, current_tz)


class CalendarEventsViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client = APIClient()
        self.url = reverse("events_feed")
        self.user = User.objects.create_user(username="events-user", password="test")
        self.room_one = Room.objects.create(name="Sala Event 1", building="A", capacity=20)
        self.room_two = Room.objects.create(name="Sala Event 2", building="B", capacity=30)

    def test_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_returns_recent_events_with_expected_metadata(self):
        self.client.force_authenticate(self.user)
        recent_start = self.make_local_datetime(days_from_now=1, hour=9)
        recent = Reservation.objects.create(
            room=self.room_one,
            user=self.user,
            title="   ",
            start=recent_start,
            end=recent_start + timedelta(hours=1),
            status=STATUS_PENDING,
            note="Notatka testowa",
        )
        old_start = self.make_local_datetime(days_from_now=-10, hour=10)
        Reservation.objects.create(
            room=self.room_two,
            user=self.user,
            title="Stare wydarzenie",
            start=old_start,
            end=old_start + timedelta(hours=1),
            status=STATUS_APPROVED,
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], recent.id)
        self.assertEqual(data[0]["title"], self.room_one.name)
        self.assertEqual(data[0]["color"], "#f97316")
        self.assertEqual(data[0]["extendedProps"]["room"], self.room_one.name)
        self.assertEqual(data[0]["extendedProps"]["user"], self.user.username)
        self.assertEqual(data[0]["extendedProps"]["note"], "Notatka testowa")

    def test_filters_events_by_room(self):
        self.client.force_authenticate(self.user)
        start = self.make_local_datetime(days_from_now=2, hour=11)
        Reservation.objects.create(
            room=self.room_one,
            user=self.user,
            title="Sala 1",
            start=start,
            end=start + timedelta(hours=1),
            status=STATUS_APPROVED,
        )
        Reservation.objects.create(
            room=self.room_two,
            user=self.user,
            title="Sala 2",
            start=start + timedelta(hours=2),
            end=start + timedelta(hours=3),
            status=STATUS_REJECTED,
        )

        response = self.client.get(self.url, {"room": self.room_two.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["extendedProps"]["room"], self.room_two.name)
        self.assertEqual(data[0]["color"], "#ef4444")

    def make_local_datetime(self, days_from_now, hour, minute=0):
        current_tz = timezone.get_current_timezone()
        target_date = timezone.localdate() + timedelta(days=days_from_now)
        naive_value = datetime.combine(target_date, time(hour=hour, minute=minute))
        return timezone.make_aware(naive_value, current_tz)
