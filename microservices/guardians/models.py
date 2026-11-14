from django.db import models


class Assignment(models.Model):
    user_id = models.PositiveIntegerField()
    room_id = models.PositiveIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user_id", "room_id"], name="unique_guardian_room")]
