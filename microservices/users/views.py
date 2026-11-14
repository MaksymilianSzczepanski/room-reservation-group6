from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError

from microservices.common import APIError, endpoint, identity, payload, response, token_for

User = get_user_model()


def as_dict(user):
    return {"id": user.id, "username": user.username, "email": user.email,
            "is_admin": user.is_staff, "is_student": user.groups.filter(name="Students").exists(),
            "is_active": user.is_active}


@endpoint(methods=("POST",), access="public")
def login(request):
    data = payload(request)
    user = authenticate(username=data.get("username", ""), password=data.get("password", ""))
    if user is None:
        raise APIError("Invalid credentials", 401)
    return response({"token": token_for(as_dict(user)), "user": as_dict(user)})


@endpoint()
def me(request):
    return response(request.actor)


@endpoint(methods=("GET", "POST"), access="admin")
def users(request):
    if request.method == "GET":
        return response([as_dict(user) for user in User.objects.all().order_by("id")])
    data = payload(request)
    if not data.get("username") or not data.get("password"):
        raise APIError("username and password required")
    if not isinstance(data.get("is_admin", False), bool) or not isinstance(data.get("is_student", False), bool):
        raise APIError("is_admin and is_student must be booleans")
    try:
        user = User.objects.create_user(
            username=data["username"], password=data["password"], email=data.get("email", ""),
            is_staff=data.get("is_admin", False),
        )
    except IntegrityError as exc:
        raise APIError("Username already exists", 409) from exc
    if data.get("is_student"):
        group, _ = Group.objects.get_or_create(name="Students")
        user.groups.add(group)
    return response(as_dict(user), 201)


@endpoint(methods=("GET", "PATCH", "DELETE"), access="admin")
def user_detail(request, user_id):
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        raise APIError("User not found", 404)
    if request.method == "DELETE":
        user.is_active = False
        user.save(update_fields=["is_active"])
        return response({"deactivated": True})
    if request.method == "PATCH":
        data = payload(request)
        for field in ("email", "first_name", "last_name", "is_active", "is_staff"):
            if field in data:
                setattr(user, field, data[field])
        if data.get("password"):
            user.set_password(data["password"])
        user.save()
        if "is_student" in data:
            group, _ = Group.objects.get_or_create(name="Students")
            if data["is_student"]:
                user.groups.add(group)
            else:
                user.groups.remove(group)
    return response(as_dict(user))


@endpoint(access="internal")
def internal_user(request, user_id):
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        raise APIError("User not found", 404)
    return response(as_dict(user))
