import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from . import STATUS_APPROVED, STATUS_REJECTED


logger = logging.getLogger(__name__)


def _reservation_time_range(reservation):
    start = timezone.localtime(reservation.start)
    end = timezone.localtime(reservation.end)
    return f"{start:%Y-%m-%d %H:%M} - {end:%H:%M}"


def _absolute_url(request, view_name):
    if request is None:
        return ""
    return request.build_absolute_uri(reverse(view_name))


def _send_reservation_email(subject, message, recipients):
    recipients = [email for email in recipients if email]
    if not recipients:
        return False

    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
    except Exception:
        logger.exception("Nie udalo sie wyslac maila rezerwacji do: %s", ", ".join(recipients))
        return False

    return True


def notify_guardians_about_new_reservation(reservation, request=None):
    recipients = list(
        reservation.room.guardians.select_related("user")
        .exclude(user__email="")
        .values_list("user__email", flat=True)
        .distinct()
    )
    dashboard_url = _absolute_url(request, "guardian_dashboard")
    message = (
        "Pojawila sie nowa prosba o rezerwacje sali.\n\n"
        f"Tytul: {reservation.title}\n"
        f"Sala: {reservation.room.name}\n"
        f"Termin: {_reservation_time_range(reservation)}\n"
        f"Rezerwujacy: {reservation.user.get_full_name() or reservation.user.username}\n"
        f"Notatka: {reservation.note or '-'}\n"
    )
    if dashboard_url:
        message += f"\nRozpatrz prosbe w panelu opiekuna: {dashboard_url}\n"

    return _send_reservation_email(
        subject=f"Nowa prosba o rezerwacje sali {reservation.room.name}",
        message=message,
        recipients=recipients,
    )


def notify_requester_about_decision(reservation, request=None):
    if reservation.status == STATUS_APPROVED:
        decision_text = "zaakceptowana"
        subject = "Rezerwacja zostala zaakceptowana"
    elif reservation.status == STATUS_REJECTED:
        decision_text = "odrzucona"
        subject = "Rezerwacja zostala odrzucona"
    else:
        return False

    calendar_url = _absolute_url(request, "calendar")
    message = (
        f"Twoja prosba o rezerwacje zostala {decision_text}.\n\n"
        f"Tytul: {reservation.title}\n"
        f"Sala: {reservation.room.name}\n"
        f"Termin: {_reservation_time_range(reservation)}\n"
    )
    if reservation.status == STATUS_REJECTED:
        message += f"Komentarz opiekuna: {reservation.decision_comment or '-'}\n"
    if calendar_url:
        message += f"\nKalendarz rezerwacji: {calendar_url}\n"

    return _send_reservation_email(
        subject=subject,
        message=message,
        recipients=[reservation.user.email],
    )
