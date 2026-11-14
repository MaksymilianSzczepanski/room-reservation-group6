from django.db import models


class Decision(models.Model):
    reservation_id = models.PositiveIntegerField(unique=True)
    guardian_id = models.PositiveIntegerField()
    status = models.CharField(max_length=20)
    comment = models.TextField(blank=True)
    applied = models.BooleanField(default=False)
    blocked = models.BooleanField(default=False)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
