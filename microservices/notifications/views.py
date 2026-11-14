from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from microservices.common import APIError, call, endpoint, payload, response
from .models import Notification


@endpoint(access="admin")
def notifications(request):
    return response(list(Notification.objects.order_by("-created_at").values(
        "id", "event_id", "recipient", "subject", "state", "error", "created_at",
    )))


@endpoint(methods=("POST",), access="internal")
def deliver(request):
    data = payload(request)
    item = data.get("reservation", {})
    kind = data.get("kind")
    if kind not in ("created", "decided") or not isinstance(item, dict) or not item.get("id"):
        raise APIError("kind and reservation required")
    if kind == "created":
        guardians = call("guardians", f"/api/guardians/internal/room/{item['room_id']}/")
        users = [call("users", f"/api/users/internal/{g['user_id']}/") for g in guardians]
        subject = "Nowa prośba o rezerwację sali"
    else:
        users = [call("users", f"/api/users/internal/{item['user_id']}/")]
        subject = f"Rezerwacja {item['status']}"
    body = f"Rezerwacja #{item['id']}: {item['title']}\nSala #{item['room_id']}\n{item['start']} – {item['end']}\nStatus: {item['status']}\n{item.get('decision_comment', '')}"
    sent = 0
    for user in users:
        email = user.get("email")
        if not email:
            continue
        event_id = f"{kind}:{item['id']}:{user['id']}"
        failure = None
        with transaction.atomic():
            notification, _ = Notification.objects.get_or_create(
                event_id=event_id,
                defaults={"recipient": email, "subject": subject, "body": body},
            )
            notification = Notification.objects.select_for_update().get(pk=notification.pk)
            if notification.state == "sent":
                continue
            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
            except Exception as exc:
                notification.state = "failed"
                notification.error = str(exc)[:500]
                notification.save(update_fields=["state", "error"])
                failure = exc
            else:
                notification.state = "sent"
                notification.error = ""
                notification.save(update_fields=["state", "error"])
                sent += 1
        if failure is not None:
            raise APIError("Email delivery failed", 503) from failure
    return response({"sent": sent})
