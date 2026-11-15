import json
from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from microservices.common import APIError, token_for
from .models import OutboxEvent, Reservation
from .views import dispatch


class ReservationAPITests(TestCase):
    def setUp(self):
        self.token = token_for({"id": 2, "is_admin": False, "is_student": False})
        day = timezone.localdate() + timedelta(days=1)
        zone = timezone.get_current_timezone()
        self.start = timezone.make_aware(datetime.combine(day, time(9)), zone)
        self.end = self.start + timedelta(hours=1)
        self.data = {"room_id": 1, "title": "Spotkanie", "start": self.start.isoformat(), "end": self.end.isoformat()}

    def test_public_calendar_exposes_only_occupied_intervals_without_personal_data(self):
        from urllib.parse import urlencode
        for status in ('pending', 'approved', 'rejected', 'cancelled'):
            Reservation.objects.create(room_id=1, user_id=2, title='Prywatny tytuł',
                                       start=self.start, end=self.end, status=status,
                                       note='Poufne uwagi', decision_comment='Komentarz')
        Reservation.objects.create(room_id=2, user_id=4, title='Inna sala', start=self.start, end=self.end)
        query = urlencode({'room_id': 1, 'start': (self.start - timedelta(days=3)).isoformat(),
                           'end': (self.end + timedelta(days=3)).isoformat()})
        result = self.client.get('/api/reservations/calendar/?' + query)
        self.assertEqual(result.status_code, 200)
        self.assertEqual([row['status'] for row in result.json()], ['pending', 'approved'])
        for row in result.json():
            self.assertEqual(set(row), {'id', 'room_id', 'start', 'end', 'status'})
        self.assertEqual(self.client.get('/api/reservations/').status_code, 401)
        self.assertEqual(self.client.post('/api/reservations/', '{}', content_type='application/json').status_code, 401)
        self.assertEqual(self.client.post('/api/reservations/calendar/?room_id=1').status_code, 405)

    def test_internal_list_filters_by_period_and_room(self):
        from urllib.parse import urlencode
        Reservation.objects.create(room_id=1, user_id=2, title='W okresie', start=self.start, end=self.end)
        Reservation.objects.create(room_id=2, user_id=2, title='Inna sala', start=self.start, end=self.end)
        Reservation.objects.create(room_id=1, user_id=2, title='Za tydzien', start=self.start + timedelta(days=7),
                                   end=self.end + timedelta(days=7))
        key = {'HTTP_X_SERVICE_KEY': 'local-service-key'}
        self.assertEqual(len(self.client.get('/api/reservations/internal/all/', **key).json()), 3)
        query = urlencode({'start': (self.start - timedelta(hours=2)).isoformat(),
                           'end': (self.end + timedelta(hours=2)).isoformat(), 'room_id': 1})
        result = self.client.get('/api/reservations/internal/all/?' + query, **key)
        self.assertEqual([row['title'] for row in result.json()], ['W okresie'])
        self.assertEqual(self.client.get('/api/reservations/internal/all/?start=x&end=y', **key).status_code, 400)

    def test_public_calendar_validates_filters(self):
        for query in ('', '?room_id=x', '?room_id=-1', '?room_id=1&start=wrong',
                      '?room_id=1&start=2026-11-01T09:00:00&end=2026-11-02T09:00:00'):
            with self.subTest(query=query):
                self.assertEqual(self.client.get('/api/reservations/calendar/' + query).status_code, 400)

    @patch("microservices.reservations.views.call", return_value={"id": 1})
    def test_conflicting_reservation_is_rejected(self, remote):
        headers = {"content_type": "application/json", "HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        first = self.client.post("/api/reservations/", json.dumps(self.data), **headers)
        second = self.client.post("/api/reservations/", json.dumps(self.data), **headers)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)

    @patch("microservices.reservations.views.call", return_value={"id": 1})
    def test_students_cannot_book(self, remote):
        student = token_for({"id": 3, "is_student": True})
        result = self.client.post(
            "/api/reservations/", json.dumps(self.data), content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {student}",
        )
        self.assertEqual(result.status_code, 403)

    @patch("microservices.reservations.views.call")
    def test_failed_notification_is_stored_for_retry(self, remote):
        remote.side_effect = [{"id": 2, "is_active": True}, {"id": 1}, APIError("notification service unavailable", 503)]
        result = self.client.post(
            "/api/reservations/", json.dumps(self.data), content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()["notification_status"], "pending_retry")
        event = OutboxEvent.objects.get()
        self.assertFalse(event.delivered)
        remote.side_effect = None
        remote.return_value = {"sent": 1}
        self.assertTrue(dispatch(event))
        event.refresh_from_db()
        self.assertTrue(event.delivered)
