import os
import csv
from dataclasses import dataclass, field
from typing import List, Optional

from django.core.management.base import BaseCommand, CommandError

from apps.advisor.models import Advisor
from clients.dso_client import DsoClient
from apps.cases.models import AdviceType, Case, CaseStatus
from apps.homeownerassociation.models import HomeownerAssociation
from datetime import datetime


months = {
    "jan": "Jan",
    "feb": "Feb",
    "mrt": "Mar",
    "apr": "Apr",
    "mei": "May",
    "jun": "Jun",
    "jul": "Jul",
    "aug": "Aug",
    "sep": "Sep",
    "okt": "Oct",
    "nov": "Nov",
    "dec": "Dec",
}


@dataclass
class ImportResult:
    total_rows: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"Import voltooid: {self.successful} succesvol, "
            f"{self.failed} mislukt, {self.skipped} overgeslagen van {self.total_rows} totaal aantal rijen"
        )


def _norm_header(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _norm_cell(value: Optional[str]) -> str:
    return (value or "").strip()


class Command(BaseCommand):
    help = "Import cases from a CSV file"

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

        if not os.path.exists(csv_file):
            raise CommandError(f"CSV file not found: {csv_file}")

        if not os.path.isfile(csv_file):
            raise CommandError(f"Path is not a file: {csv_file}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Running in DRY-RUN mode (no data will be saved)")
            )

        self.stdout.write(f"Importing cases from: {csv_file}")
        result = ImportResult()
        dso_client = DsoClient()

        try:
            with open(csv_file, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f, delimiter=";")
                if not reader.fieldnames:
                    raise CommandError("CSV-bestand heeft geen headers")

                headers = [_norm_header(h) for h in reader.fieldnames]
                if "statutaire naam" not in headers:
                    raise CommandError(
                        "Ontbrekende verplichte kolom: 'Statutaire naam'. "
                        f"Gevonden kolommen: {', '.join(reader.fieldnames)}"
                    )
                status_closed = CaseStatus.objects.get(
                    name="Afgesloten",
                )
                for idx, row in enumerate(reader, start=2):
                    result.total_rows += 1
                    row_norm = {
                        _norm_header(k): _norm_cell(v) for k, v in (row or {}).items()
                    }

                    vve_name = row_norm.get("statutaire naam")
                    already_in_zwd = row_norm.get("zwd?")
                    creation_date = row_norm.get("aanmelding ontvangen")
                    legacy_id = row_norm.get("dossier nummer")
                    advisor = row_norm.get("naam bedrijf")
                    if creation_date is None or creation_date == "":
                        result.skipped += 1
                        continue
                    for nl, en in months.items():
                        creation_date = creation_date.replace(nl, en)

                    date_obj = datetime.strptime(creation_date, "%d-%b-%y")

                    creation_date = date_obj.date()
                    if already_in_zwd and already_in_zwd.lower() in ("ja"):
                        result.skipped += 1
                        continue
                    if not vve_name or vve_name.lower() in ("0"):
                        result.skipped += 1
                        continue

                    try:
                        dso_objects = dso_client.get_hoa_by_name(vve_name)
                    except Exception:
                        result.failed += 1
                        result.errors.append(
                            f"Rij {idx} Lookup failed for '{vve_name}'"
                        )
                        continue

                    homeowner_association = HomeownerAssociation.objects.filter(
                        name__iexact=vve_name
                    ).first()

                    if homeowner_association is None:
                        bag_id = (
                            (dso_objects[0] or {}).get("votIdentificatie")
                            if dso_objects
                            else None
                        )
                        if not bag_id:
                            result.failed += 1
                            result.errors.append(
                                f"Rij {idx}, veld 'statutaire naam': DSO returned no BAG identificatie; cannot create homeowner association"
                            )
                            continue
                        if not dry_run:
                            homeowner_association = (
                                HomeownerAssociation().get_or_create_hoa_by_bag_id(
                                    bag_id
                                )
                            )
                    existing_case = Case.objects.filter(
                        advice_type=AdviceType.OUD.value,
                        homeowner_association=homeowner_association,
                    ).first()

                    if existing_case:
                        result.skipped += 1
                        continue

                    if not dry_run and advisor:
                        advisor, _ = Advisor.objects.get_or_create(
                            name=advisor, enabled=False
                        )

                    if not dry_run:
                        # atomic..
                        case = Case.objects.create(
                            advice_type=AdviceType.OUD.value,
                            homeowner_association=homeowner_association,
                            created=creation_date,
                            legacy_id=legacy_id,
                            advisor=advisor if advisor else None,
                        )
                        case.workflows.all().delete()
                        case.end_date = creation_date
                        case.status = status_closed
                        case.save()

                    result.successful += 1

        except UnicodeDecodeError as exc:
            raise CommandError(f"Fout bij het lezen van CSV-bestand: {exc}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(str(result)))
        self.stdout.write("")

        if result.errors:
            self.stdout.write(self.style.ERROR(f"Errors ({len(result.errors)}):"))
            for error in result.errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            self.stdout.write("")

        if result.failed > 0:
            self.stdout.write(
                self.style.ERROR(f"Import completed with {result.failed} error(s).")
            )
        elif result.successful > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully imported {result.successful} cases.")
            )
        else:
            self.stdout.write(self.style.WARNING("No cases were imported."))
