from datetime import time

from django.db import connection, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from microservices.common import APIError, call, endpoint, payload, response
from .models import OutboxEvent, Reservation


def as_dict(item):
    return {"id": item.id, "room_id": item.room_id, "user_id": item.user_id,
            "title": item.title, "start": item.start.isoformat(), "end": item.end.isoformat(),
            "status": item.status, "note": item.note, "decision_comment": item.decision_comment}


@endpoint(access="public")
def calendar(request):
    """Public availability, without applicant details, notes or decision comments."""
    try:
        room_id = int(request.GET["room_id"])
        if room_id <= 0:
            raise ValueError
    except (KeyError, ValueError, TypeError) as exc:
        raise APIError("Valid room_id required") from exc
    qs = Reservation.objects.filter(room_id=room_id, status__in=[Reservation.PENDING, Reservation.APPROVED])
    # Calendar views span multiple days, unlike individual reservation requests.
    start, end = request.GET.get("start"), request.GET.get("end")
    if start or end:
        try:
            start, end = parse_datetime(start or ""), parse_datetime(end or "")
        except ValueError as exc:
            raise APIError("Valid calendar range required") from exc
        if not start or not end or timezone.is_naive(start) or timezone.is_naive(end) or end <= start:
            raise APIError("Valid calendar range with timezone required")
        qs = qs.filter(start__lt=end, end__gt=start)
    return response([{"id": item.id, "room_id": item.room_id,
                      "start": item.start.isoformat(), "end": item.end.isoformat(),
                      "status": item.status} for item in qs.order_by("start")])


@endpoint(access="public")
def calendar(request):
    """Public availability, without applicant details, notes or decision comments."""
    try:
        room_id = int(request.GET["room_id"])
        if room_id <= 0:
            raise ValueError
    except (KeyError, ValueError, TypeError) as exc:
        raise APIError("Valid room_id required") from exc
    qs = Reservation.objects.filter(room_id=room_id, status__in=[Reservation.PENDING, Reservation.APPROVED])
    # Calendar views span multiple days, unlike individual reservation requests.
    start, end = request.GET.get("start"), request.GET.get("end")
    if start or end:
        try:
            start, end = parse_datetime(start or ""), parse_datetime(end or "")
        except ValueError as exc:
            raise APIError("Valid calendar range required") from exc
        if not start or not end or timezone.is_naive(start) or timezone.is_naive(end) or end <= start:
            raise APIError("Valid calendar range with timezone required")
        qs = qs.filter(start__lt=end, end__gt=start)
    return response([{"id": item.id, "room_id": item.room_id,
                      "start": item.start.isoformat(), "end": item.end.isoformat(),
                      "status": item.status} for item in qs.order_by("start")])


def dispatch(event):
    try:
        call("notifications", "/api/notifications/internal/", "POST", {"kind": event.kind, "reservation": event.data})
    except APIError as exc:
        event.attempts += 1
        event.last_error = str(exc)
        event.save(update_fields=["attempts", "last_error"])
        return False
    event.attempts += 1
    event.delivered = True
    event.last_error = ""
    event.save(update_fields=["attempts", "delivered", "last_error"])
    return True


def interval(data):
    start, end = parse_datetime(data.get("start", "")), parse_datetime(data.get("end", ""))
    if not start or not end or timezone.is_naive(start) or timezone.is_naive(end) or end <= start:
        raise APIError("Valid start and end with timezone required")
    local_start, local_end = timezone.localtime(start), timezone.localtime(end)
    if local_start.date() != local_end.date() or local_start.time() < time(7) or local_end.time() > time(22):
        raise APIError("Reservations must fit one day between 07:00 and 22:00")
    return start, end


@endpoint(methods=("GET", "POST"))
def reservations(request):
    if request.method == "GET":
        qs = Reservation.objects.order_by("start")
        if request.GET.get("room_id"):
            qs = qs.filter(room_id=request.GET["room_id"])
        return response([as_dict(item) for item in qs])
    if request.actor.get("is_student"):
        raise APIError("Students cannot create reservations", 403)
    user = call("users", f"/api/users/internal/{request.actor['id']}/")
    if user.get("is_active") is False:
        raise APIError("Inactive user cannot create reservations", 403)
    data = payload(request)
    try:
        room_id = int(data["room_id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise APIError("room_id required") from exc
    call("rooms", f"/api/rooms/{room_id}/")
    start, end = interval(data)
    title = str(data.get("title", "")).strip()
    if not title:
        raise APIError("title required")
    with transaction.atomic():
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [room_id])
        conflict = Reservation.objects.filter(
            room_id=room_id, status__in=[Reservation.PENDING, Reservation.APPROVED],
            start__lt=end, end__gt=start,
        ).exists()
        if conflict:
            raise APIError("Room is already reserved", 409)
        item = Reservation.objects.create(
            room_id=room_id, user_id=request.actor["id"], title=title,
            start=start, end=end, note=str(data.get("note", "")),
        )
        result = as_dict(item)
        event = OutboxEvent.objects.create(event_id=f"created:{item.id}", kind="created", data=result)
    result["notification_status"] = "sent" if dispatch(event) else "pending_retry"
    return response(result, 201)


@endpoint(methods=("GET", "DELETE"))
def reservation_detail(request, reservation_id):
    item = Reservation.objects.filter(pk=reservation_id).first()
    if item is None:
        raise APIError("Reservation not found", 404)
    if request.method == "DELETE":
        with transaction.atomic():
            item = Reservation.objects.select_for_update().get(pk=reservation_id)
            if request.actor["id"] != item.user_id and not request.actor.get("is_admin"):
                raise APIError("Not permitted", 403)
            if item.status not in [Reservation.PENDING, Reservation.APPROVED]:
                raise APIError("Reservation cannot be cancelled", 409)
            item.status = Reservation.CANCELLED
            item.save(update_fields=["status"])
    return response(as_dict(item))


@endpoint(access="internal")
def internal_detail(request, reservation_id):
    item = Reservation.objects.filter(pk=reservation_id).first()
    if item is None:
        raise APIError("Reservation not found", 404)
    return response(as_dict(item))


@endpoint(methods=("POST",), access="internal")
def apply_decision(request, reservation_id):
    data = payload(request)
    if data.get("status") not in (Reservation.APPROVED, Reservation.REJECTED):
        raise APIError("Invalid decision")
    comment = str(data.get("comment", ""))
    if data["status"] == Reservation.REJECTED and not comment:
        raise APIError("Rejection comment required")
    with transaction.atomic():
        item = Reservation.objects.select_for_update().filter(pk=reservation_id).first()
        if item is None:
            raise APIError("Reservation not found", 404)
        if item.status != Reservation.PENDING:
            if item.status == data["status"] and item.decision_comment == comment:
                return response(as_dict(item))
            raise APIError("Reservation already decided", 409)
        item.status = data["status"]
        item.decision_comment = comment
        item.save(update_fields=["status", "decision_comment"])
        result = as_dict(item)
        event = OutboxEvent.objects.create(event_id=f"decided:{item.id}", kind="decided", data=result)
    result["notification_status"] = "sent" if dispatch(event) else "pending_retry"
    return response(result)


@endpoint(access="internal")
def room_usage(request, room_id):
    return response({"used": Reservation.objects.filter(room_id=room_id).exists()})


@endpoint(access="internal")
def occupied(request):
    start, end = interval(request.GET)
    qs = Reservation.objects.filter(status__in=[Reservation.PENDING, Reservation.APPROVED], start__lt=end, end__gt=start)
    return response(sorted(set(qs.values_list("room_id", flat=True))))


@endpoint(access="internal")
def all_reservations(request):
    return response([as_dict(item) for item in Reservation.objects.order_by("id")])
