from django.db import models


class Reservation(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    room_id = models.PositiveIntegerField(db_index=True)
    user_id = models.PositiveIntegerField(db_index=True)
    title = models.CharField(max_length=200)
    start = models.DateTimeField()
    end = models.DateTimeField()
    status = models.CharField(max_length=20, default=PENDING)
    note = models.TextField(blank=True)
    decision_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["room_id", "start", "end"])]


class OutboxEvent(models.Model):
    event_id = models.CharField(max_length=100, unique=True)
    kind = models.CharField(max_length=20)
    data = models.JSONField()
    delivered = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
