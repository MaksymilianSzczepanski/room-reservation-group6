from django.db import models


class Notification(models.Model):
    event_id = models.CharField(max_length=100, unique=True)
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    state = models.CharField(max_length=20, default="pending")
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
