from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("room_reservations", "0003_attribute_and_room_attributes"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
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
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
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
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
