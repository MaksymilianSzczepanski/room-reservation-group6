from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.utils.dateparse import parse_datetime

from microservices.common import APIError, call, endpoint, response

ZONE = ZoneInfo("Europe/Warsaw")
OPEN, CLOSE = time(7), time(22)
HOURS_PER_DAY = 15
MAX_DAYS = 366


@endpoint(access="admin")
def report(request):
    rooms = call("rooms", "/api/rooms/")
    reservations = call("reservations", "/api/reservations/internal/all/")
    counts = Counter(item["room_id"] for item in reservations if item["status"] == "approved")
    statuses = Counter(item["status"] for item in reservations)
    return response({
        "room_count": len(rooms),
        "reservation_count": len(reservations),
        "status_counts": dict(statuses),
        "approved_by_room": [
            {"room_id": room["id"], "room_name": room["name"], "count": counts[room["id"]]}
            for room in rooms
        ],
    })


def parse_day(value, name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise APIError(f"Invalid {name}") from exc


def percent(part, whole):
    return round(100 * part / whole, 1) if whole else 0.0


def visible_rooms(request):
    """Administrators see every room; guardians only the rooms assigned to them."""
    rooms = call("rooms", "/api/rooms/")
    if not request.actor.get("is_admin"):
        assigned = {item["room_id"] for item in call("guardians", f"/api/guardians/internal/user/{request.actor['id']}/")}
        if not assigned:
            raise APIError("Not a guardian of any room", 403)
        rooms = [room for room in rooms if room["id"] in assigned]
    wanted = request.GET.getlist("room_id")
    if wanted:
        try:
            wanted = {int(value) for value in wanted}
        except ValueError as exc:
            raise APIError("Invalid room_id") from exc
        rooms = [room for room in rooms if room["id"] in wanted]
        if len(rooms) != len(wanted):
            raise APIError("Not a guardian of this room", 403)
    return rooms


@endpoint()
def occupancy(request):
    """Share of bookable time (07:00-22:00, Warsaw) taken by reservations in a date range."""
    first = parse_day(request.GET.get("start"), "start")
    last = parse_day(request.GET.get("end"), "end")
    if last < first:
        raise APIError("End date must not be before start date")
    if (last - first).days + 1 > MAX_DAYS:
        raise APIError("Date range is limited to 366 days")
    workdays = request.GET.get("workdays") in {"1", "true", "yes"}
    days = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
    days = [day for day in days if not workdays or day.weekday() < 5]
    included = set(days)
    rooms = visible_rooms(request)

    hours = defaultdict(lambda: {"approved": 0.0, "pending": 0.0, "count": 0})
    weekday_hours = defaultdict(float)
    if rooms and days:
        query = [("start", datetime.combine(first, OPEN, ZONE).isoformat()),
                 ("end", datetime.combine(last, CLOSE, ZONE).isoformat())]
        query += [("room_id", room["id"]) for room in rooms]
        for item in call("reservations", "/api/reservations/internal/all/?" + urlencode(query)):
            if item["status"] not in ("approved", "pending"):
                continue
            start = parse_datetime(item["start"]).astimezone(ZONE)
            end = parse_datetime(item["end"]).astimezone(ZONE)
            if start.date() not in included:
                continue
            start = max(start, datetime.combine(start.date(), OPEN, ZONE))
            end = min(end, datetime.combine(start.date(), CLOSE, ZONE))
            length = max((end - start).total_seconds() / 3600, 0)
            hours[item["room_id"]][item["status"]] += length
            if item["status"] == "approved":
                hours[item["room_id"]]["count"] += 1
                weekday_hours[start.weekday()] += length

    available = len(days) * HOURS_PER_DAY
    result_rooms = []
    for room in rooms:
        value = hours[room["id"]]
        result_rooms.append({
            "room_id": room["id"], "name": room["name"], "building": room.get("building", ""),
            "capacity": room.get("capacity", 0), "available_hours": available,
            "approved_hours": round(value["approved"], 2), "pending_hours": round(value["pending"], 2),
            "reservation_count": value["count"],
            "occupancy": percent(value["approved"], available),
            "pending_share": percent(value["pending"], available),
        })
    result_rooms.sort(key=lambda item: (-item["occupancy"], item["name"]))

    total_available = available * len(rooms)
    total_approved = sum(item["approved_hours"] for item in result_rooms)
    total_pending = sum(item["pending_hours"] for item in result_rooms)
    day_counts = Counter(day.weekday() for day in days)
    by_weekday = [{
        "weekday": weekday,
        "available_hours": day_counts[weekday] * HOURS_PER_DAY * len(rooms),
        "approved_hours": round(weekday_hours[weekday], 2),
        "occupancy": percent(weekday_hours[weekday], day_counts[weekday] * HOURS_PER_DAY * len(rooms)),
    } for weekday in range(7) if day_counts[weekday]]

    return response({
        "start": first.isoformat(), "end": last.isoformat(), "workdays_only": workdays,
        "day_count": len(days), "hours_per_day": HOURS_PER_DAY,
        "total": {
            "room_count": len(rooms), "available_hours": total_available,
            "approved_hours": round(total_approved, 2), "pending_hours": round(total_pending, 2),
            "reservation_count": sum(item["reservation_count"] for item in result_rooms),
            "occupancy": percent(total_approved, total_available),
            "pending_share": percent(total_pending, total_available),
        },
        "rooms": result_rooms,
        "by_weekday": by_weekday,
    })
