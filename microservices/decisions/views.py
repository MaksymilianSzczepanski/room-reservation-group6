from django.db import IntegrityError

from microservices.common import APIError, call, endpoint, payload, response
from .models import Decision


def apply_record(item):
    try:
        changed = call(
            "reservations", f"/api/reservations/internal/{item.reservation_id}/decision/", "POST",
            {"status": item.status, "comment": item.comment},
        )
    except APIError as exc:
        item.blocked = exc.status == 409
        item.last_error = str(exc)
        item.save(update_fields=["blocked", "last_error"])
        return None
    item.applied = True
    item.last_error = ""
    item.save(update_fields=["applied", "last_error"])
    return changed


@endpoint(methods=("GET", "POST"))
def decisions(request):
    if request.method == "GET":
        qs = Decision.objects.order_by("-created_at")
        if not request.actor.get("is_admin"):
            qs = qs.filter(guardian_id=request.actor["id"])
        return response(list(qs.values("id", "reservation_id", "guardian_id", "status", "comment", "applied", "blocked", "last_error", "created_at")))
    data = payload(request)
    try:
        reservation_id = int(data["reservation_id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise APIError("reservation_id required") from exc
    status = data.get("status")
    comment = str(data.get("comment", "")).strip()
    if status not in ("approved", "rejected") or (status == "rejected" and not comment):
        raise APIError("Approved or rejected status required; rejection needs comment")
    reservation = call("reservations", f"/api/reservations/internal/{reservation_id}/")
    if reservation["status"] != "pending":
        raise APIError("Reservation already decided", 409)
    assigned = call(
        "guardians",
        f"/api/guardians/internal/check/?user_id={request.actor['id']}&room_id={reservation['room_id']}",
    )
    if not assigned["assigned"]:
        raise APIError("Not a guardian of this room", 403)
    try:
        item = Decision.objects.create(
            reservation_id=reservation_id, guardian_id=request.actor["id"],
            status=status, comment=comment,
        )
    except IntegrityError as exc:
        raise APIError("Decision already recorded", 409) from exc
    changed = apply_record(item)
    if changed is None:
        if item.blocked:
            return response({"id": item.id, "error": item.last_error}, 409)
        return response({"id": item.id, "status": "pending_retry"}, 202)
    return response({"id": item.id, "reservation": changed}, 201)
