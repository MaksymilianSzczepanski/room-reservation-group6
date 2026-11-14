"""Retry durable notification events while the reservation service is running."""
import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "microservices.settings")

import django  # noqa: E402

django.setup()

from microservices.reservations.models import OutboxEvent  # noqa: E402
from microservices.reservations.views import dispatch  # noqa: E402

while True:
    for event in OutboxEvent.objects.filter(delivered=False).order_by("created_at")[:50]:
        dispatch(event)
    time.sleep(10)
