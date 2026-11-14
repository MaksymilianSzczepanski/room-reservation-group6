"""Retry decisions recorded before a reservation service outage."""
import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "microservices.settings")

import django  # noqa: E402

django.setup()

from microservices.decisions.models import Decision  # noqa: E402
from microservices.decisions.views import apply_record  # noqa: E402

while True:
    for item in Decision.objects.filter(applied=False, blocked=False).order_by("created_at")[:50]:
        apply_record(item)
    time.sleep(10)
