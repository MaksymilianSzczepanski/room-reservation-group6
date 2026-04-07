from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("security", "0002_alter_user_groups_alter_user_user_permissions"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="role",
        ),
        migrations.DeleteModel(
            name="Role",
        ),
    ]
