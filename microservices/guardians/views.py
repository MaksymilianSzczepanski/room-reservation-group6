from django.db import IntegrityError

from microservices.common import APIError, call, endpoint, payload, response
from .models import Assignment


def as_dict(item):
    return {"id": item.id, "user_id": item.user_id, "room_id": item.room_id}


@endpoint()
def my_assignments(request):
    return response([as_dict(item) for item in
                     Assignment.objects.filter(user_id=request.actor["id"]).order_by("id")])


@endpoint(methods=("GET", "POST"), access="admin")
def assignments(request):
    if request.method == "GET":
        qs = Assignment.objects.all().order_by("id")
        if request.GET.get("room_id"):
            qs = qs.filter(room_id=request.GET["room_id"])
        return response([as_dict(item) for item in qs])
    data = payload(request)
    try:
        user_id, room_id = int(data["user_id"]), int(data["room_id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise APIError("user_id and room_id required") from exc
    user = call("users", f"/api/users/internal/{user_id}/")
    if user.get("is_active") is False:
        raise APIError("Inactive user cannot be assigned", 409)
    call("rooms", f"/api/rooms/{room_id}/")
    try:
        item = Assignment.objects.create(user_id=user_id, room_id=room_id)
    except IntegrityError as exc:
        raise APIError("Guardian already assigned", 409) from exc
    return response(as_dict(item), 201)


@endpoint(methods=("DELETE",), access="admin")
def assignment_detail(request, assignment_id):
    deleted, _ = Assignment.objects.filter(pk=assignment_id).delete()
    if not deleted:
        raise APIError("Assignment not found", 404)
    return response({"deleted": True})


@endpoint(access="internal")
def check(request):
    user_id = request.GET.get("user_id")
    room_id = request.GET.get("room_id")
    if not user_id or not room_id:
        raise APIError("user_id and room_id required")
    return response({"assigned": Assignment.objects.filter(user_id=user_id, room_id=room_id).exists()})


@endpoint(access="internal")
def for_user(request, user_id):
    return response([as_dict(item) for item in Assignment.objects.filter(user_id=user_id).order_by("room_id")])


@endpoint(access="internal")
def for_room(request, room_id):
    return response([as_dict(item) for item in Assignment.objects.filter(room_id=room_id)])
