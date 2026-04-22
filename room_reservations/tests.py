from datetime import timedelta

from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from . import STATUS_APPROVED, STATUS_PENDING, STATUS_REJECTED
from .models import Reservation, Room, RoomGuardian


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
        students_group = Group.objects.create(name="Students")
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
        start = timezone.now() + timedelta(days=days_from_now)
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

    def create_pending_reservation(self):
        start = timezone.now() + timedelta(days=3)
        return Reservation.objects.create(
            room=self.room,
            user=self.employee,
            title="Konsultacje",
            start=start,
            end=start + timedelta(hours=1),
            status=STATUS_PENDING,
        )
