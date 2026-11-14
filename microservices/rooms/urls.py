from django.urls import path
from . import views

urlpatterns = [
    path("", views.rooms),
    path("attributes/", views.attributes),
    path("<int:room_id>/", views.room_detail),
]
