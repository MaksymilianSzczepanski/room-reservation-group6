import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create an optional initial employee from environment variables without changing existing credentials."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_EMPLOYEE_USERNAME", "").strip()
        password = os.environ.get("DJANGO_EMPLOYEE_PASSWORD", "")
        if not username and not password:
            self.stdout.write("Initial employee not configured")
            return
        if not username or not password:
            raise CommandError("Both DJANGO_EMPLOYEE_USERNAME and DJANGO_EMPLOYEE_PASSWORD are required")
        users = get_user_model()
        existing = users.objects.filter(username=username).first()
        if existing:
            if existing.is_staff or existing.is_superuser or not existing.is_active or existing.groups.filter(name="Students").exists():
                raise CommandError("Configured username belongs to an inactive account or a different role")
            self.stdout.write("Employee already exists; credentials unchanged")
            return
        users.objects.create_user(username=username, password=password,
                                  email=os.environ.get("DJANGO_EMPLOYEE_EMAIL", ""))
        self.stdout.write("Initial employee created")
