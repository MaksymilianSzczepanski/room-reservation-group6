from django.urls import path
from . import views

urlpatterns = [
    path("", views.notifications),
    path("internal/", views.deliver),
]
