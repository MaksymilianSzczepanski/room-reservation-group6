from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login),
    path("me/", views.me),
    path("", views.users),
    path("<int:user_id>/", views.user_detail),
    path("internal/<int:user_id>/", views.internal_user),
]
