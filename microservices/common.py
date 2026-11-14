"""Small shared transport and authentication layer for the Django services."""
import json
import os
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.core import signing
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

AUTH_SALT = "room-reservation-api-v1"


class APIError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def response(value, status=200):
    return JsonResponse(value, safe=not isinstance(value, list), status=status, encoder=DjangoJSONEncoder)


def payload(request):
    try:
        result = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError) as exc:
        raise APIError("Invalid JSON") from exc
    if not isinstance(result, dict):
        raise APIError("Expected a JSON object")
    return result


def token_for(user):
    return signing.dumps(user, key=os.environ.get("AUTH_SIGNING_KEY", "local-signing-key"), salt=AUTH_SALT)


def identity(request):
    value = request.headers.get("Authorization", "")
    if not value.startswith("Bearer "):
        raise APIError("Bearer token required", 401)
    try:
        return signing.loads(
            value[7:], key=os.environ.get("AUTH_SIGNING_KEY", "local-signing-key"),
            salt=AUTH_SALT, max_age=3600,
        )
    except signing.BadSignature as exc:
        raise APIError("Invalid or expired token", 401) from exc


def endpoint(methods=("GET",), access="user"):
    def decorate(view):
        @csrf_exempt
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            try:
                if request.method not in methods:
                    raise APIError("Method not allowed", 405)
                if access == "internal":
                    if request.headers.get("X-Service-Key") != os.environ.get("SERVICE_KEY", "local-service-key"):
                        raise APIError("Service key required", 403)
                elif access != "public":
                    request.actor = identity(request)
                    if access == "admin" and not request.actor.get("is_admin"):
                        raise APIError("Administrator required", 403)
                return view(request, *args, **kwargs)
            except APIError as exc:
                return response({"error": str(exc)}, exc.status)
        return wrapped
    return decorate


def service_url(name):
    catalog = os.environ.get("CONSUL_HTTP_ADDR", "http://consul:8500")
    try:
        with urlopen(f"{catalog}/v1/health/service/{quote(name)}?passing=true", timeout=2) as result:
            instances = json.load(result)
    except (URLError, ValueError) as exc:
        raise APIError(f"Service discovery unavailable: {name}", 503) from exc
    if not instances:
        raise APIError(f"Service unavailable: {name}", 503)
    service = instances[0]["Service"]
    address = service.get("Address") or instances[0]["Node"]["Address"]
    return f"http://{address}:{service['Port']}"


def call(name, path, method="GET", data=None):
    body = None if data is None else json.dumps(data, cls=DjangoJSONEncoder).encode("utf-8")
    request = Request(
        service_url(name) + path, data=body, method=method,
        headers={"Content-Type": "application/json", "X-Service-Key": os.environ.get("SERVICE_KEY", "local-service-key")},
    )
    try:
        with urlopen(request, timeout=4) as result:
            return json.load(result)
    except HTTPError as exc:
        try:
            detail = json.load(exc)
        except ValueError:
            detail = {}
        raise APIError(detail.get("error", f"{name} returned {exc.code}"), exc.code if exc.code < 500 else 502) from exc
    except (URLError, TimeoutError) as exc:
        raise APIError(f"Service unavailable: {name}", 503) from exc
