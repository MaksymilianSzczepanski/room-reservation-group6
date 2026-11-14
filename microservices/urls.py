from django.http import JsonResponse
from django.urls import include, path
from .settings import SERVICE_NAME


def health(_request):
    return JsonResponse({"service": SERVICE_NAME, "status": "ok"})


urlpatterns = [
    path("health/", health),
    path(f"api/{SERVICE_NAME}/", include(f"microservices.{SERVICE_NAME}.urls")),
]
if SERVICE_NAME == "portal":
    urlpatterns.append(path("", include("microservices.portal.urls")))
