import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.homeownerassociation.importers.letter_importer import LetterImporter


class Command(BaseCommand):
    help = "Import homeowner association letters from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str, help="Path to the CSV file to import")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run in dry-run mode (validate but do not save data)",
        )
        parser.add_argument(
            "--date",
            type=str,
            required=True,
            help="Date for all communication notes (format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)",
        )
        parser.add_argument(
            "--description",
            type=str,
            required=True,
            help="Description/note text for all communication notes",
        )
        parser.add_argument(
            "--author-name",
            type=str,
            required=True,
            help="Author name string for all communication notes",
        )
        parser.add_argument(
            "--skip-hoa-api",
            action="store_true",
            help="Skip fetching HOA data from the DSO API",
        )

    def _parse_date(self, date_string: str) -> datetime:
        """
        Parse date string in format YYYY-MM-DD or YYYY-MM-DD HH:MM:SS.
        If no time is provided, defaults to 08:00:00.
        Returns timezone-aware datetime object.
        """
        date_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
        ]

        for date_format in date_formats:
            try:
                naive_dt = datetime.strptime(date_string, date_format)
                # If only date was provided (no time), default to 08:00:00
                if date_format == "%Y-%m-%d":
                    naive_dt = naive_dt.replace(hour=8, minute=0, second=0)
                # Make the datetime timezone-aware using Django's timezone
                return timezone.make_aware(naive_dt)
            except ValueError:
                continue

        raise CommandError(
            f"Invalid date format: '{date_string}'. "
            f"Expected format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"
        )

    def handle(self, *args, **options):
        csv_file = options["file"]
        dry_run = options["dry_run"]
        date_string = options["date"]
        description = options["description"]
        author_name = options["author_name"]
        skip_hoa_api = options["skip_hoa_api"]

        # Validate file exists
        if not os.path.exists(csv_file):
            raise CommandError(f"CSV file not found: {csv_file}")

        if not os.path.isfile(csv_file):
            raise CommandError(f"Path is not a file: {csv_file}")

        # Parse date
        try:
            parsed_date = self._parse_date(date_string)
        except CommandError:
            raise

        # Validate description and author_name are not empty
        if not description.strip():
            raise CommandError("Description cannot be empty")

        if not author_name.strip():
            raise CommandError("Author name cannot be empty")

        # Create importer and run import
        importer = LetterImporter(
            date=parsed_date,
            description=description,
            author_name=author_name,
            dry_run=dry_run,
            skip_hoa_api=skip_hoa_api,
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Running in DRY-RUN mode (no data will be saved)")
            )

        self.stdout.write(f"Importing letters from: {csv_file}\n\n")
        self.stdout.write(f"Date: {parsed_date}")
        self.stdout.write(f"Author: {author_name}")
        self.stdout.write(f"Description: {description}\n\n")

        self.stdout.write(
            f"Running import now. Results will be shown shortly, please stay tuned...\n\n"
        )
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

        # Output messages (including skipped duplicates)
        if result.messages:
            self.stdout.write(self.style.SUCCESS(f"Messages ({len(result.messages)}):"))
            for message in result.messages:
                self.stdout.write(f"  - {message}")
            self.stdout.write("")

        # Output warnings
        if result.warnings:
            self.stdout.write(self.style.WARNING(f"Warnings ({len(result.warnings)}):"))
            for warning in result.warnings:
                self.stdout.write(self.style.WARNING(f"  - {warning}"))
            self.stdout.write("")

        # Summary
        summary_parts = []
        if result.successful > 0:
            summary_parts.append(
                f"{result.successful} communication notes imported successfully"
            )
        if result.skipped > 0:
            summary_parts.append(f"{result.skipped} skipped (duplicates)")
        if result.failed > 0:
            summary_parts.append(f"{result.failed} failed")

        if result.failed > 0:
            self.stdout.write(
                self.style.ERROR(f"Import completed: {', '.join(summary_parts)}.")
            )
        elif result.successful > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Import completed: {', '.join(summary_parts)}.")
            )
        else:
            self.stdout.write(
                self.style.WARNING("No communication notes were imported.")
            )
