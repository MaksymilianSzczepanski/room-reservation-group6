from django.db import migrations


def _run_postgres_sql(schema_editor, sql):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(sql)


def drop_legacy_attributes_column(apps, schema_editor):
    _run_postgres_sql(
        schema_editor,
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'room_reservations_room'
                  AND column_name = 'attributes'
            ) THEN
                ALTER TABLE room_reservations_room DROP COLUMN attributes;
            END IF;
        END$$;
        """,
    )


def ensure_attribute_tables(apps, schema_editor):
    _run_postgres_sql(
        schema_editor,
        """
        CREATE TABLE IF NOT EXISTS room_reservations_attribute (
            id bigserial PRIMARY KEY,
            name varchar(50) NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS room_reservations_room_attributes (
            id bigserial PRIMARY KEY,
            room_id bigint NOT NULL REFERENCES room_reservations_room(id) DEFERRABLE INITIALLY DEFERRED,
            attribute_id bigint NOT NULL REFERENCES room_reservations_attribute(id) DEFERRABLE INITIALLY DEFERRED
        );

        CREATE UNIQUE INDEX IF NOT EXISTS room_reservations_room_attributes_room_id_attribute_id_uniq
            ON room_reservations_room_attributes (room_id, attribute_id);
        """,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("room_reservations", "0003_attribute_and_room_attributes"),
    ]

    operations = [
        migrations.RunPython(drop_legacy_attributes_column, migrations.RunPython.noop),
        migrations.RunPython(ensure_attribute_tables, migrations.RunPython.noop),
    ]
