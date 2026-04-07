from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from room_reservations.views import AttributeViewSet, ModalLoginView, ReservationViewSet, RoomViewSet

router = DefaultRouter()
router.register(r'rooms', RoomViewSet, basename='rooms')
router.register(r'reservations', ReservationViewSet, basename='reservations')
router.register(r'attributes', AttributeViewSet, basename='attributes')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/modal-login/', ModalLoginView.as_view(), name='modal_login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('api/', include(router.urls)),
    path('', include('room_reservations.urls')),
]
