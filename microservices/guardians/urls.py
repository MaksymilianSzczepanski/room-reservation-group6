from django.urls import path
from . import views

urlpatterns = [
    path("", views.assignments),
    path("mine/", views.my_assignments),
    path("<int:assignment_id>/", views.assignment_detail),
    path("internal/check/", views.check),
    path("internal/room/<int:room_id>/", views.for_room),
]
