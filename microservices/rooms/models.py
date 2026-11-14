from django.db import models


class Attribute(models.Model):
    name = models.CharField(max_length=100, unique=True)


class Room(models.Model):
    name = models.CharField(max_length=100, unique=True)
    building = models.CharField(max_length=100, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    attributes = models.ManyToManyField(Attribute, blank=True)
