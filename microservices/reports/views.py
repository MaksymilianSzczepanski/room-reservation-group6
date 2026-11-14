from collections import Counter

from microservices.common import call, endpoint, response


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
