from django.urls import path

from . import views

urlpatterns = [
    path("", views.SearchView.as_view(), name="search"),
    path("calendar/", views.CalendarView.as_view(), name="calendar"),
    path("guardian/", views.GuardianDashboardView.as_view(), name="guardian_dashboard"),
    path(
        "guardian/reservations/<int:reservation_id>/decision/",
        views.GuardianReservationDecisionView.as_view(),
        name="guardian_reservation_decision",
    ),
    path("api/events/", views.CalendarEventsView.as_view(), name="events_feed"),
]
