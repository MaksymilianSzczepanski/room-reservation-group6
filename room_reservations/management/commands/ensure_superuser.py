import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import ProgrammingError


class Command(BaseCommand):
    help = "Create a default superuser from environment variables if it does not exist."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

        if not all([username, email, password]):
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_SUPERUSER_USERNAME / EMAIL / PASSWORD not set; skipping superuser creation."
                )
            )
            return

        User = get_user_model()

        try:
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.SUCCESS(f"Superuser '{username}' already exists; skipping creation.")
                )
                return

            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
        except ProgrammingError:
            # Happens when auth tables are missing (migrations not applied yet).
            self.stderr.write(
                self.style.ERROR(
                    "Auth tables missing. Run migrations first: `python manage.py migrate` inside the container."
                )
            )
            return
