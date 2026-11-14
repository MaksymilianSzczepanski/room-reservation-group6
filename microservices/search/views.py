from urllib.parse import urlencode

from microservices.common import call, endpoint, response


@endpoint(access="public")
def search(request):
    query = urlencode([(key, value) for key, values in request.GET.lists() for value in values])
    rooms = call("rooms", "/api/rooms/" + ("?" + query if query else ""))
    start, end = request.GET.get("start"), request.GET.get("end")
    if start and end:
        occupied = set(call("reservations", "/api/reservations/internal/occupied/?" + urlencode({"start": start, "end": end})))
        rooms = [room for room in rooms if room["id"] not in occupied]
    return response(rooms)
