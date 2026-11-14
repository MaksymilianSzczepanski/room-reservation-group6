from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError

from microservices.common import APIError, call, endpoint, identity, payload, response
from .models import Attribute, Room


def as_dict(room):
    return {"id": room.id, "name": room.name, "building": room.building,
            "capacity": room.capacity, "description": room.description,
            "attributes": [{"id": attr.id, "name": attr.name} for attr in room.attributes.all()]}


def admin(request):
    if not identity(request).get("is_admin"):
        raise APIError("Administrator required", 403)


def fill(room, data):
    for field in ("name", "building", "capacity", "description"):
        if field in data:
            setattr(room, field, data[field])
    if not room.name:
        raise APIError("name required")
    ids = data.get("attribute_ids")
    if ids is not None:
        if not isinstance(ids, list):
            raise APIError("Invalid attribute_ids")
        try:
            ids = [int(value) for value in ids]
        except (TypeError, ValueError) as exc:
            raise APIError("Invalid attribute_ids") from exc
        if len(set(ids)) != len(ids) or Attribute.objects.filter(id__in=ids).count() != len(ids):
            raise APIError("Invalid attribute_ids")
    try:
        with transaction.atomic():
            room.full_clean()
            room.save()
            if ids is not None:
                room.attributes.set(ids)
    except (ValueError, IntegrityError, ValidationError) as exc:
        raise APIError("Invalid or duplicate room", 400) from exc
    return room


@endpoint(methods=("GET", "POST"), access="public")
def rooms(request):
    if request.method == "POST":
        admin(request)
        return response(as_dict(fill(Room(), payload(request))), 201)
    qs = Room.objects.prefetch_related("attributes").order_by("name")
    args = request.GET
    if args.get("building__icontains"):
        qs = qs.filter(building__icontains=args["building__icontains"])
    if args.get("name__icontains"):
        qs = qs.filter(name__icontains=args["name__icontains"])
    for key, lookup in (("capacity__gte", "capacity__gte"), ("capacity__lte", "capacity__lte")):
        if args.get(key):
            try:
                qs = qs.filter(**{lookup: int(args[key])})
            except ValueError as exc:
                raise APIError(f"Invalid {key}") from exc
    ids = args.getlist("attributes__id")
    for attr_id in ids:
        try:
            qs = qs.filter(attributes__id=int(attr_id))
        except ValueError as exc:
            raise APIError("Invalid attributes__id") from exc
    return response([as_dict(room) for room in qs.distinct()])


@endpoint(methods=("GET", "POST"), access="public")
def attributes(request):
    if request.method == "POST":
        admin(request)
        name = payload(request).get("name", "").strip()
        if not name:
            raise APIError("name required")
        try:
            attr = Attribute.objects.create(name=name)
        except IntegrityError as exc:
            raise APIError("Attribute already exists", 409) from exc
        return response({"id": attr.id, "name": attr.name}, 201)
    return response(list(Attribute.objects.order_by("name").values("id", "name")))


@endpoint(methods=("GET", "PATCH", "DELETE"), access="public")
def room_detail(request, room_id):
    room = Room.objects.prefetch_related("attributes").filter(pk=room_id).first()
    if room is None:
        raise APIError("Room not found", 404)
    if request.method != "GET":
        admin(request)
        if request.method == "DELETE":
            usage = call("reservations", f"/api/reservations/internal/room/{room_id}/usage/")
            assignments = call("guardians", f"/api/guardians/internal/room/{room_id}/")
            if usage["used"] or assignments:
                raise APIError("Room is used by reservations or guardians", 409)
            room.delete()
            return response({"deleted": True})
        room = fill(room, payload(request))
    return response(as_dict(room))
