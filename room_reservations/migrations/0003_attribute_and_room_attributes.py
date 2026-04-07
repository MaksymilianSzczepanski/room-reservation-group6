from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("room_reservations", "0002_rename_room_reser_room_id_5ed067_idx_room_reserv_room_id_17806d_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="Attribute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="room",
            name="attributes",
            field=models.ManyToManyField(
                blank=True,
                help_text="Lista atrybutów sali, np. komputer, rzutnik, mikroskop, tablica.",
                related_name="rooms",
                to="room_reservations.attribute",
            ),
        ),
    ]
