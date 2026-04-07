from rest_framework import serializers

from . import STATUS_APPROVED, STATUS_PENDING
from .models import Attribute, Reservation, Room


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ["id", "name"]


class RoomSerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = ["id", "name", "building", "capacity", "description", "attributes"]


class ReservationSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source="room.name", read_only=True)
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "room",
            "room_name",
            "user",
            "title",
            "start",
            "end",
            "status",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "created_at", "updated_at", "user"]

    def create(self, validated_data):
        validated_data.setdefault("status", STATUS_PENDING)
        return super().create(validated_data)

    def validate(self, attrs):
        room = attrs.get("room") or getattr(self.instance, "room", None)
        start = attrs.get("start") or getattr(self.instance, "start", None)
        end = attrs.get("end") or getattr(self.instance, "end", None)

        if start and end and end <= start:
            raise serializers.ValidationError("Koniec rezerwacji musi byc po czasie poczatku.")

        if room and start and end:
            overlapping = (
                Reservation.objects.filter(room=room, status__in=[STATUS_PENDING, STATUS_APPROVED])
                .exclude(id=getattr(self.instance, "id", None))
                .filter(start__lt=end, end__gt=start)
            )
            if overlapping.exists():
                raise serializers.ValidationError("Sala jest juz zarezerwowana w wybranym zakresie czasu.")

        return attrs
