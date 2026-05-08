from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import Attribute, Reservation, Room, RoomGuardian


class RoomAdminChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        if obj.building:
            return f"{obj.name} ({obj.building})"
        return obj.name


class RoomAdminMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        if obj.building:
            return f"{obj.name} ({obj.building})"
        return obj.name


class RoomGuardianAdminForm(forms.ModelForm):
    room = RoomAdminChoiceField(queryset=Room.objects.order_by("name", "building"), required=False)
    rooms = RoomAdminMultipleChoiceField(
        queryset=Room.objects.order_by("name", "building"),
        required=False,
        widget=FilteredSelectMultiple("Sale", is_stacked=False),
        label="Sale",
        help_text="Mozesz zaznaczyc kilka sal naraz.",
    )

    class Meta:
        model = RoomGuardian
        fields = ("user", "room", "rooms")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["room"].required = True
            self.fields["rooms"].widget = forms.MultipleHiddenInput()
            self.fields["rooms"].help_text = ""
        else:
            self.fields["room"].widget = forms.HiddenInput()
            self.fields["rooms"].required = True

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get("user")

        if self.instance and self.instance.pk:
            if not cleaned_data.get("room"):
                self.add_error("room", "Wybierz sale.")
            return cleaned_data

        rooms = cleaned_data.get("rooms")
        if not rooms:
            self.add_error("rooms", "Wybierz przynajmniej jedna sale.")
            return cleaned_data

        if user:
            existing_rooms = Room.objects.filter(guardians__user=user, pk__in=rooms.values_list("pk", flat=True)).order_by("name")
            if existing_rooms.exists():
                room_labels = ", ".join(RoomAdminMultipleChoiceField(queryset=Room.objects.none()).label_from_instance(room) for room in existing_rooms)
                self.add_error("rooms", f"Ten uzytkownik ma juz przypisane sale: {room_labels}.")

        return cleaned_data


class RoomLabelAdminMixin:
    room_search_fields = ("room__name", "room__building")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "room":
            kwargs["form_class"] = RoomAdminChoiceField
            kwargs.setdefault("queryset", Room.objects.order_by("name", "building"))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


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
class RoomGuardianAdmin(RoomLabelAdminMixin, admin.ModelAdmin):
    form = RoomGuardianAdminForm
    list_display = ("user", "room")
    search_fields = ("user__username", "room__name", "room__building")
    list_filter = ("room",)

    def get_fields(self, request, obj=None):
        if obj is None:
            return ("user", "rooms")
        return ("user", "room")

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return

        rooms = list(form.cleaned_data["rooms"])
        obj.room = rooms[0]
        super().save_model(request, obj, form, change)

        extra_assignments = [
            RoomGuardian(user=obj.user, room=room)
            for room in rooms[1:]
        ]
        if extra_assignments:
            RoomGuardian.objects.bulk_create(extra_assignments)

        self.message_user(request, f"Dodano przypisanie opiekuna do {len(rooms)} sal.")


@admin.register(Reservation)
class ReservationAdmin(RoomLabelAdminMixin, admin.ModelAdmin):
    list_display = ("title", "room", "user", "start", "end", "status")
    list_filter = ("status", "room")
    search_fields = ("title", "room__name", "room__building", "user__username")

