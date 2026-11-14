"""Exercise the eight services through the API gateway.

Usage: API_URL=http://localhost:8002 python scripts/smoke_microservices.py
Reads DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD from the environment.
"""
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE = os.environ.get("API_URL", "http://localhost:8002").rstrip("/")


def api(path, method="GET", data=None, token=None):
    request = Request(
        BASE + path,
        data=None if data is None else json.dumps(data).encode(),
        method=method,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    try:
        with urlopen(request, timeout=10) as result:
            return json.load(result)
    except HTTPError as exc:
        raise RuntimeError(f"{method} {path}: HTTP {exc.code}: {exc.read().decode()}") from exc


def main():
    if "DJANGO_SUPERUSER_USERNAME" not in os.environ:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    admin_name = os.environ["DJANGO_SUPERUSER_USERNAME"]
    admin_password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
    for attempt in range(30):
        try:
            admin = api("/api/users/login/", "POST", {"username": admin_name, "password": admin_password})
            break
        except (RuntimeError, OSError):
            if attempt == 29:
                raise
            time.sleep(1)
    admin_token = admin["token"]
    marker = secrets.token_hex(4)
    worker_name = "worker_" + marker
    worker_password = secrets.token_urlsafe(18)
    worker = api("/api/users/", "POST", {
        "username": worker_name, "password": worker_password,
        "email": f"{worker_name}@example.test",
    }, admin_token)
    worker_token = api("/api/users/login/", "POST", {
        "username": worker_name, "password": worker_password,
    })["token"]
    room = api("/api/rooms/", "POST", {"name": "Demo " + marker, "building": "A", "capacity": 20}, admin_token)
    api("/api/guardians/", "POST", {"user_id": admin["user"]["id"], "room_id": room["id"]}, admin_token)
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    available = api("/api/search/?" + urlencode({"start": start.isoformat(), "end": end.isoformat()}))
    assert any(item["id"] == room["id"] for item in available), "New room should be available"
    booking = api("/api/reservations/", "POST", {
        "room_id": room["id"], "title": "Test między usługami",
        "start": start.isoformat(), "end": end.isoformat(),
    }, worker_token)
    assert booking["status"] == "pending"
    public_calendar = api(f"/api/reservations/calendar/?room_id={room['id']}")
    assert any(item["id"] == booking["id"] for item in public_calendar), "Anonymous calendar should show occupied interval"
    assert all(set(item) == {"id", "room_id", "start", "end", "status"} for item in public_calendar), "Public calendar must not expose private details"
    assert booking["notification_status"] == "sent", "Guardian notification was not delivered"
    unavailable = api("/api/search/?" + urlencode({"start": start.isoformat(), "end": end.isoformat()}))
    assert all(item["id"] != room["id"] for item in unavailable), "Reserved room should be hidden"
    decision = api("/api/decisions/", "POST", {
        "reservation_id": booking["id"], "status": "approved",
    }, admin_token)
    assert decision["reservation"]["status"] == "approved"
    assert decision["reservation"]["notification_status"] == "sent", "Decision notification was not delivered"
    report = api("/api/reports/", token=admin_token)
    assert report["reservation_count"] >= 1
    notifications = api("/api/notifications/", token=admin_token)
    assert len(notifications) >= 1
    print(json.dumps({
        "result": "ok", "room_id": room["id"], "worker_id": worker["id"],
        "reservation_id": booking["id"], "notification_count": len(notifications),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
