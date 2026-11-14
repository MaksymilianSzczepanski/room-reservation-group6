"""Register a healthy container in Consul for peer lookup and gateway routing."""
import json
import os
import time
from urllib.request import Request, urlopen

from microservices.settings import SERVICE_NAME

address = os.environ.get("SERVICE_ADDRESS", SERVICE_NAME)
catalog = os.environ.get("CONSUL_HTTP_ADDR", "http://consul:8500")
definition = {
    "ID": SERVICE_NAME,
    "Name": SERVICE_NAME,
    "Address": address,
    "Port": 8000,
    "Tags": [
        "traefik.enable=true",
        f"traefik.http.routers.{SERVICE_NAME}.rule=PathPrefix(`/api/{SERVICE_NAME}/`)",
        f"traefik.http.routers.{SERVICE_NAME}.entrypoints=web",
        f"traefik.http.services.{SERVICE_NAME}.loadbalancer.server.port=8000",
    ],
    "Check": {"HTTP": f"http://{address}:8000/health/", "Interval": "5s", "Timeout": "2s"},
}
if SERVICE_NAME == "portal":
    definition["Tags"][1] = "traefik.http.routers.portal.rule=PathPrefix(`/`)"
    definition["Tags"].append("traefik.http.routers.portal.priority=1")
for attempt in range(30):
    try:
        request = Request(
            catalog + "/v1/agent/service/register",
            data=json.dumps(definition).encode(), method="PUT",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=3):
            break
    except OSError:
        if attempt == 29:
            raise
        time.sleep(2)
