from datetime import datetime
from typing import Dict, Optional
from django.db import transaction
from apps.cases.models import Case
from apps.homeownerassociation.models import Contact, HomeownerAssociation
from .base import BaseImporter


class CourseParticipantImporter(BaseImporter):
    """Importer for course participants CSV files"""

    COLUMNS_REQUIRED = [
        "ZWD",  # @TODO not sure if this will be there
        "Vnummer",  # @TODO not sure if this will be there
        "Statutaire Naam",
        "Kontaktpersoon",
        "Mailadres",
        "Cursusdatum",
    ]

    COLUMN_MAPPING = {
        "case_prefixed_dossier_id": "ZWD",
        "case_legacy_id": "Vnummer",
        "hoa_name": "Statutaire Naam",
        "contact_fullname": "Kontaktpersoon",
        "contact_email": "Mailadres",
        "course_date": "Cursusdatum",
    }

    def __init__(self, dry_run: bool = False, skip_hoa_api: bool = False):
        super().__init__(self.COLUMNS_REQUIRED, dry_run=dry_run)
        self.skip_hoa_api = skip_hoa_api

    def _find_homeowner_association(
        self, row: Dict[str, str], row_number: int
    ) -> Optional[HomeownerAssociation]:
        """
        Find HomeownerAssociation using:

        1. `ZWD` (case prefixed_dossier_id, e.g. "123EAK")
        2. `Vnummer` (case legacy_id, e.g. "V12345")
        3. `Statutaire Naam` (exact match, e.g. "Vereniging van Eigenaars van X")
        """
        prefixed_dossier_id = row.get(
            self.COLUMN_MAPPING["case_prefixed_dossier_id"], ""
        ).strip()
        legacy_id = row.get(self.COLUMN_MAPPING["case_legacy_id"], "").strip()
        hoa_name = row.get(self.COLUMN_MAPPING["hoa_name"], "").strip()

        # Try to find by `ZWD` (Case `prefixed_dossier_id`)
        if prefixed_dossier_id and prefixed_dossier_id != "0":
            try:
                case = Case.objects.filter(
                    prefixed_dossier_id__iexact=prefixed_dossier_id
                ).first()
                if case and case.homeowner_association:
                    return case.homeowner_association
                elif case and not case.homeowner_association:
                    self._add_warning(
                        f"Rij {row_number}: Zaak {prefixed_dossier_id} gevonden maar heeft geen vve"
                    )
            except Exception as e:
                self._add_warning(
                    f"Rij {row_number}: Fout bij het opzoeken van zaak {prefixed_dossier_id}: {str(e)}"
                )

        # Try to find by `Vnummer` (Case `legacy_id`)
        if legacy_id and legacy_id != "0":
            try:
                case = Case.objects.filter(legacy_id__iexact=legacy_id).first()
                if case and case.homeowner_association:
                    return case.homeowner_association
            except Exception as e:
                self._add_warning(
                    f"Rij {row_number}: Fout bij het opzoeken van zaak {legacy_id}: {str(e)}"
                )

        # Try to find by `Statutaire Naam` (HomeownerAssociation `name`, exact match with DSO API fallback)
        if hoa_name:
            hoa = self._find_homeowner_association_by_name(
                hoa_name, row_number, skip_hoa_api=self.skip_hoa_api
            )
            if hoa:
                return hoa

        return None

    def _parse_course_date(
        self, date_string: str, row_number: int
    ) -> Optional[datetime]:
        """
        Parse course date from CSV format (e.g., "25/11/2025 00:00").
        Returns datetime object or None if parsing fails.
        """
        if not date_string or not date_string.strip():
            return None

        date_string = date_string.strip()

        # Try to parse formats: "25/11/2025 00:00" or "25/11/2025"
        try:
            # First try with time component
            if " " in date_string:
                date_part = date_string.split(" ")[0]
            else:
                date_part = date_string

            # Parse DD/MM/YYYY format
            return datetime.strptime(date_part, "%d/%m/%Y")
        except ValueError:
            return None

    def _process_row(self, row: Dict[str, str], row_number: int) -> bool:
        """
        Process a single course participant row and return a boolean indicating if the row was processed successfully.
        """
        email = row.get(self.COLUMN_MAPPING["contact_email"], "").strip()

        if not email:
            self._add_error(
                row_number,
                self.COLUMN_MAPPING["contact_email"],
                "E-mailadres is verplicht",
            )
            return False

        if not self._validate_email(email):
            self._add_error(
                row_number,
                self.COLUMN_MAPPING["contact_email"],
                f"Ongeldig e-mailadres formaat: {email}",
            )
            return False

        fullname = row.get(self.COLUMN_MAPPING["contact_fullname"], "").strip() or ""

        # Parse course date - required field
        course_date_str = row.get(self.COLUMN_MAPPING["course_date"], "").strip()
        if not course_date_str:
            self._add_error(
                row_number,
                self.COLUMN_MAPPING["course_date"],
                "Cursusdatum is verplicht",
            )
            return False

        course_date = self._parse_course_date(course_date_str, row_number)
        if not course_date:
            self._add_error(
                row_number,
                self.COLUMN_MAPPING["course_date"],
                f"Ongeldig cursusdatum formaat: '{course_date_str}'. Verwacht formaat: DD/MM/YYYY",
            )
            return False

        # Find `HomeownerAssociation`
        hoa_name = row.get(self.COLUMN_MAPPING["hoa_name"], "").strip()
        hoa = self._find_homeowner_association(row, row_number)
        if not hoa:
            self._add_error(
                row_number,
                None,
                f"Kon vve niet vinden voor '{hoa_name}'",
            )
            return False

        # Set defaults, since these are not in the CSV or optional
        role = "Vve-lid"

        try:
            if self.dry_run:
                course_date_str = course_date.strftime("%Y-%m-%d")
                self._add_message(
                    f"Rij {row_number}: [DRY RUN] Zou contact {email} aanmaken/bijwerken "
                    f"voor vve {hoa.name} met cursusdatum {course_date_str}"
                )
            else:
                with transaction.atomic():
                    contact = Contact.objects.filter(
                        email__iexact=email,
                        homeowner_association=hoa,
                    ).first()

                    if contact:
                        # Update existing contact
                        # Note: we preserve existing values if not present in the CSV
                        contact.fullname = fullname or contact.fullname
                        contact.role = contact.role or role
                        contact.course_date = course_date.date()
                        contact.save()
                    else:
                        # Create new contact
                        contact = Contact.objects.create(
                            email=email,
                            fullname=fullname,
                            phone="",
                            role=role,
                            homeowner_association=hoa,
                            course_date=course_date.date(),
                        )

            return True

        except Exception as e:
            self._add_error(
                row_number, None, f"Fout bij het opslaan van contact: {str(e)}"
            )
            return False
