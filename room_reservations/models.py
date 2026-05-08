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

RESERVATION_START_HOUR = 7
RESERVATION_END_HOUR = 22


def get_reservation_hours_error(start, end):
    if not start or not end:
        return None

    local_start = timezone.localtime(start) if timezone.is_aware(start) else timezone.make_aware(start)
    local_end = timezone.localtime(end) if timezone.is_aware(end) else timezone.make_aware(end)

    if local_start.date() != local_end.date():
        return "Rezerwacja musi miescic sie w jednym dniu i godzinach 07:00-22:00."

    start_minutes = (local_start.hour * 60) + local_start.minute
    end_minutes = (local_end.hour * 60) + local_end.minute
    allowed_start_minutes = RESERVATION_START_HOUR * 60
    allowed_end_minutes = RESERVATION_END_HOUR * 60

    if start_minutes < allowed_start_minutes or end_minutes > allowed_end_minutes:
        return "Rezerwacje sa mozliwe tylko w godzinach 07:00-22:00."

    return None


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
    decision_comment = models.TextField(
        blank=True,
        help_text="Komentarz opiekuna przy decyzji, np. powod odrzucenia.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start"]
        indexes = [models.Index(fields=["room", "start", "end"])]

    def clean(self):
        if self.end <= self.start:
            raise ValidationError("End time must be after start time.")

        hours_error = get_reservation_hours_error(self.start, self.end)
        if hours_error:
            raise ValidationError(hours_error)

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


