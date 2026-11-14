import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the initial API administrator from environment variables, if absent."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        if not username or not password:
            self.stdout.write("Initial administrator credentials not configured")
            return
        user_model = get_user_model()
        if not user_model.objects.filter(username=username).exists():
            user_model.objects.create_superuser(username=username, password=password, email=email)
            self.stdout.write("Initial administrator created")
