from django.urls import path
from . import views

urlpatterns = [
    path("", views.reservations),
    path("calendar/", views.calendar),
    path("calendar/", views.calendar),
    path("<int:reservation_id>/", views.reservation_detail),
    path("internal/<int:reservation_id>/", views.internal_detail),
    path("internal/<int:reservation_id>/decision/", views.apply_decision),
    path("internal/room/<int:room_id>/usage/", views.room_usage),
    path("internal/occupied/", views.occupied),
    path("internal/all/", views.all_reservations),
]
