from django.urls import path
from . import views

urlpatterns = [
    path("", views.report),
    path("occupancy/", views.occupancy),
]
