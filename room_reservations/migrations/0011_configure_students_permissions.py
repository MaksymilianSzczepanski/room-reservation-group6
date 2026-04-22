from django.db import migrations


STUDENT_GROUP_NAME = "Students"


def configure_students_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Reservation = apps.get_model("room_reservations", "Reservation")

    db_alias = schema_editor.connection.alias
    reservation_type, _ = ContentType.objects.using(db_alias).get_or_create(
        app_label=Reservation._meta.app_label,
        model=Reservation._meta.model_name,
    )

    view_permission, _ = Permission.objects.using(db_alias).get_or_create(
        content_type=reservation_type,
        codename="view_reservation",
        defaults={"name": "Can view reservation"},
    )

    write_permissions = Permission.objects.using(db_alias).filter(
        content_type=reservation_type,
        codename__in=["add_reservation", "change_reservation", "delete_reservation"],
    )

    students_group, _ = Group.objects.using(db_alias).get_or_create(name=STUDENT_GROUP_NAME)
    students_group.permissions.remove(*write_permissions)
    students_group.permissions.add(view_permission)


class Migration(migrations.Migration):
    dependencies = [
        ("room_reservations", "0010_alter_reservation_title_final"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(configure_students_permissions, migrations.RunPython.noop),
    ]
