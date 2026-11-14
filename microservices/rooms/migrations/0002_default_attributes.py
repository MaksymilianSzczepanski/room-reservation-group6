from django.db import migrations

DEFAULT_ATTRIBUTES = [
    "Komputer",
    "Rzutnik",
    "Mikroskop",
    "Tablica",
    "Dostęp Wi-Fi",
    "Nagłośnienie",
    "Kamera",
    "Drukarka 3D",
]


def create_defaults(apps, schema_editor):
    Attribute = apps.get_model("rooms", "Attribute")
    for name in DEFAULT_ATTRIBUTES:
        Attribute.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [("rooms", "0001_initial")]

    operations = [migrations.RunPython(create_defaults, migrations.RunPython.noop)]
