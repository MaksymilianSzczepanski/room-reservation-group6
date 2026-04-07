from django.contrib import admin
from .models import Attribute, Reservation, Room, RoomGuardian


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "building", "capacity")
    search_fields = ("name", "building")
    filter_horizontal = ("attributes",)


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(RoomGuardian)
class RoomGuardianAdmin(admin.ModelAdmin):
    list_display = ("user", "room")
    search_fields = ("user__username", "room__name")
    list_filter = ("room",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("title", "room", "user", "start", "end", "status")
    list_filter = ("status", "room")
    search_fields = ("title", "room__name", "user__username")

