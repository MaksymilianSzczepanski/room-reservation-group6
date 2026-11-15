import json
import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
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

    def test_employee_can_login_but_cannot_manage_accounts(self):
        created = self.client.post('/api/users/', json.dumps({
            'username': 'employee', 'password': 'employee-test', 'is_admin': False, 'is_student': False,
        }), content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(created.status_code, 201)
        login = self.client.post('/api/users/login/', json.dumps({
            'username': 'employee', 'password': 'employee-test',
        }), content_type='application/json')
        self.assertEqual(login.status_code, 200)
        self.assertFalse(login.json()['user']['is_admin'])
        self.assertFalse(login.json()['user']['is_student'])
        headers = {'HTTP_AUTHORIZATION': f"Bearer {login.json()['token']}"}
        self.assertEqual(self.client.get('/api/users/me/', **headers).json()['username'], 'employee')
        self.assertEqual(self.client.get('/api/users/', **headers).status_code, 403)

    @patch.dict(os.environ, {'DJANGO_EMPLOYEE_USERNAME': 'employee', 'DJANGO_EMPLOYEE_PASSWORD': 'initial-pass'})
    def test_initial_employee_is_created_once_without_resetting_password(self):
        call_command('ensure_employee', stdout=StringIO())
        user = get_user_model().objects.get(username='employee')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('initial-pass'))
        user.set_password('changed-pass')
        user.save()
        call_command('ensure_employee', stdout=StringIO())
        user.refresh_from_db()
        self.assertTrue(user.check_password('changed-pass'))
        self.assertEqual(get_user_model().objects.filter(username='employee').count(), 1)

    @patch.dict(os.environ, {'DJANGO_EMPLOYEE_USERNAME': 'admin', 'DJANGO_EMPLOYEE_PASSWORD': 'other-pass'})
    def test_initial_employee_does_not_modify_an_administrator(self):
        with self.assertRaises(CommandError):
            call_command('ensure_employee', stdout=StringIO())
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_superuser)
        self.assertTrue(self.admin.check_password('secret'))
