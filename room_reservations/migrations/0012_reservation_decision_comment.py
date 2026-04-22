from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("room_reservations", "0011_configure_students_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="reservation",
            name="decision_comment",
            field=models.TextField(
                blank=True,
                help_text="Komentarz opiekuna przy decyzji, np. powod odrzucenia.",
            ),
        ),
    ]
