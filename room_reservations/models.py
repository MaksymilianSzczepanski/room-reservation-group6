from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from . import (
    STATUS_APPROVED,
    STATUS_CANCELLED,
    STATUS_CHOICES,
    STATUS_PENDING,
    STATUS_REJECTED,
)


class Attribute(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    building = models.CharField(max_length=100, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    attributes = models.ManyToManyField(
        Attribute,
        related_name="rooms",
        blank=True,
        help_text="Lista atrybutow sali, np. komputer, rzutnik, mikroskop, tablica.",
    )

    def __str__(self):
        return self.name


class RoomGuardian(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guarded_rooms",
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="guardians")

    class Meta:
        unique_together = ("user", "room")

    def __str__(self):
        return f"{self.user.username} opiekuje się {self.room.name}"


class Reservation(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="reservations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    start = models.DateTimeField()
    end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    title = models.CharField(max_length=200, help_text="Tytul rezerwacji.")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start"]
        indexes = [models.Index(fields=["room", "start", "end"])]

    def clean(self):
        if self.end <= self.start:
            raise ValidationError("End time must be after start time.")

        overlapping = (
            Reservation.objects.filter(room=self.room)
            .exclude(id=self.id)
            .filter(
                status__in=[STATUS_PENDING, STATUS_APPROVED],
                start__lt=self.end,
                end__gt=self.start,
            )
        )
        if overlapping.exists():
            raise ValidationError("This room is already reserved for the selected time range.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_future(self):
        return self.start > timezone.now()

    def __str__(self):
        return f"{self.room} | {self.start:%Y-%m-%d %H:%M} - {self.end:%Y-%m-%d %H:%M}"


