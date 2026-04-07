from django.core.management.base import BaseCommand

from room_reservations.models import Attribute, Room


class Command(BaseCommand):
    help = "Create sample rooms with attributes for demo purposes."

    BUILDING_DISTRIBUTION = [
        ("Wydzial Informatyki", 14),
        ("Wydzial Matematyki", 8),
        ("Wydzial Fizyki", 7),
        ("Wydzial Chemii", 6),
        ("Wydzial Biologii", 5),
        ("Biblioteka Glowna", 4),
        ("Centrum Jezykowe", 3),
        ("Aula Glowna", 3),
    ]

    ATTRIBUTE_NAMES = [
        "Komputer",
        "Rzutnik",
        "Mikroskop",
        "Tablica",
        "Dostep Wi-Fi",
        "Naglosnienie",
        "Kamera",
        "Drukarka 3D",
    ]

    CAPACITIES = [12, 16, 20, 24, 30, 40, 60, 80, 120, 160]

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Number of sample rooms to create/update (default: 50).",
        )

    def handle(self, *args, **options):
        count = max(1, options["count"])

        attributes = []
        for name in self.ATTRIBUTE_NAMES:
            attr, _ = Attribute.objects.get_or_create(name=name)
            attributes.append(attr)

        buildings = self._build_building_list(count)

        created_count = 0
        updated_count = 0

        for idx in range(1, count + 1):
            building = buildings[idx - 1]
            name = f"Sala {idx:03d}"
            capacity = self.CAPACITIES[(idx - 1) % len(self.CAPACITIES)]
            description = f"Przykladowa sala {idx} w budynku: {building}."

            room, created = Room.objects.update_or_create(
                name=name,
                defaults={
                    "building": building,
                    "capacity": capacity,
                    "description": description,
                },
            )

            attr_count = 2 + (idx % 3)
            start = (idx - 1) % len(attributes)
            selected = [attributes[(start + step) % len(attributes)] for step in range(attr_count)]
            room.attributes.set(selected)

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Sample rooms ready. Created: {created_count}, updated: {updated_count}, total touched: {count}."
            )
        )

    def _build_building_list(self, count):
        buildings = []
        for building, qty in self.BUILDING_DISTRIBUTION:
            buildings.extend([building] * qty)

        if len(buildings) < count:
            i = 0
            while len(buildings) < count:
                buildings.append(self.BUILDING_DISTRIBUTION[i % len(self.BUILDING_DISTRIBUTION)][0])
                i += 1

        return buildings[:count]
