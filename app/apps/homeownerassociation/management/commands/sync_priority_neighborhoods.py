from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.homeownerassociation.models import District, Neighborhood


class Command(BaseCommand):
    help = (
        "Create or update Neighborhoods from neighborhood.txt and set "
        "priority_neighborhood=true. Districts are matched by name."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            nargs="?",
            type=str,
            default=None,
            help=(
                "Path to neighborhood.txt. "
                "Expected format: alternating lines of neighborhood name and district name."
            ),
        )
        parser.add_argument(
            "--file",
            dest="file_option",
            type=str,
            default=None,
            help=(
                "Path to neighborhood.txt (defaults to <repo-root>/neighborhood.txt). "
                "Expected format: alternating lines of neighborhood name and district name."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report changes without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if options["file"] and options["file_option"]:
            raise CommandError("Provide either FILE or --file, not both.")

        file_arg = options["file_option"] or options["file"]
        file_path = Path(file_arg)

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise CommandError(f"Path is not a file: {file_path}")

        lines = [
            line.strip()
            for line in file_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(lines) % 2 != 0:
            raise CommandError(
                f"Expected an even number of non-empty lines, got {len(lines)}. "
                "Format must be alternating neighborhood name and district name."
            )

        pairs = list(zip(lines[0::2], lines[1::2]))

        district_names = {district_name for _, district_name in pairs}
        districts = District.objects.filter(name__in=district_names)
        district_by_name = {district.name: district for district in districts}
        missing_districts = district_names.difference(district_by_name.keys())
        if missing_districts:
            missing = ", ".join(sorted(missing_districts))
            raise CommandError(
                "Some districts were not found in the database: "
                f"{missing}. Create them first, then re-run this command."
            )

        self.stdout.write(
            f"Reading {len(pairs)} neighborhood/district pairs from: {file_path}"
        )
        if dry_run:
            self.stdout.write(
                self.style.WARNING("Running in DRY-RUN mode (no changes will be saved)")
            )

        created = 0
        updated = 0
        unchanged = 0

        with transaction.atomic():
            for neighborhood_name, district_name in pairs:
                district = district_by_name[district_name]

                neighborhood = Neighborhood.objects.filter(
                    name=neighborhood_name, district=district
                ).first()
                if neighborhood is None:
                    created += 1
                    if not dry_run:
                        Neighborhood.objects.create(
                            name=neighborhood_name,
                            district=district,
                            priority_neighborhood=True,
                        )
                    continue

                if neighborhood.priority_neighborhood:
                    unchanged += 1
                    continue

                updated += 1
                if not dry_run:
                    neighborhood.priority_neighborhood = True
                    neighborhood.save(update_fields=["priority_neighborhood"])

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Priority neighborhoods sync complete"))
        self.stdout.write(f"Created:   {created}")
        self.stdout.write(f"Updated:   {updated}")
        self.stdout.write(f"Unchanged: {unchanged}")
