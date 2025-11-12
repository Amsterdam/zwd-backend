import os
from django.core.management.base import BaseCommand, CommandError
from apps.homeownerassociation.importers.contact_importer import ContactImporter


class Command(BaseCommand):
    help = "Import homeowner association contacts from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to the CSV file to import")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run in dry-run mode (validate but do not save data)",
        )

    def handle(self, *args, **options):
        csv_file = options["file"]
        dry_run = options["dry_run"]

        # Validate file exists
        if not os.path.exists(csv_file):
            raise CommandError(f"CSV file not found: {csv_file}")

        if not os.path.isfile(csv_file):
            raise CommandError(f"Path is not a file: {csv_file}")

        # Create importer and run import
        importer = ContactImporter(dry_run=dry_run)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Running in DRY-RUN mode (no data will be saved)")
            )

        self.stdout.write(f"Importing contacts from: {csv_file}")
        result = importer.import_file(csv_file)

        # Output results
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(str(result)))
        self.stdout.write("")

        # Output errors
        if result.errors:
            self.stdout.write(self.style.ERROR(f"Errors ({len(result.errors)}):"))
            for error in result.errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            self.stdout.write("")

        # Output warnings
        if result.warnings:
            self.stdout.write(self.style.WARNING(f"Warnings ({len(result.warnings)}):"))
            for warning in result.warnings:
                self.stdout.write(self.style.WARNING(f"  - {warning}"))
            self.stdout.write("")

        # Summary
        if result.failed > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"Import completed with {result.failed} error(s). "
                    f"{result.successful} contact(s) imported successfully."
                )
            )
        elif result.successful > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully imported {result.successful} contact(s)."
                )
            )
        else:
            self.stdout.write(self.style.WARNING("No contacts were imported."))
