import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from microservices.common import token_for


class UserAPITests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("admin", "admin@example.test", "secret")
        self.token = token_for({"id": self.admin.id, "username": "admin", "is_admin": True, "is_student": False})

    def test_login_and_admin_user_creation(self):
        login = self.client.post("/api/users/login/", json.dumps({"username": "admin", "password": "secret"}), content_type="application/json")
        self.assertEqual(login.status_code, 200)
        self.assertIn("token", login.json())
        created = self.client.post(
            "/api/users/", json.dumps({"username": "worker", "password": "secret", "is_student": True}),
            content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.json()["is_student"])

    def test_user_creation_requires_admin(self):
        denied = self.client.post("/api/users/", "{}", content_type="application/json")
        self.assertEqual(denied.status_code, 401)
