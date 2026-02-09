from datetime import datetime
from typing import Dict, Optional
from django.db import transaction
from apps.homeownerassociation.models import Contact, HomeownerAssociation
from .base import BaseImporter


class CourseParticipantImporter(BaseImporter):
    """
    Importer for course participant CSV files.
    Creates or updates a `Contact` for each course participant.
    """

    COLUMNS_REQUIRED = [
        "naam",
        "email",
        "cursusdatum",
        "vve",
    ]

    COLUMN_MAPPING = {
        "hoa_name": "vve",
        "contact_fullname": "naam",
        "contact_email": "email",
        "contact_phone": "telefoon",
        "contact_role": "functie",
        "course_date": "cursusdatum",
    }

    DEFAULT_ROLE = "Vve-lid"

    def __init__(self, dry_run: bool = False, skip_hoa_api: bool = False):
        super().__init__(self.COLUMNS_REQUIRED, dry_run=dry_run)
        self.skip_hoa_api = skip_hoa_api

    def _find_homeowner_association(
        self, row: Dict[str, str], row_number: int
    ) -> Optional[HomeownerAssociation]:
        """
        Find HomeownerAssociation by name in database or fetch via DSO API.
        """
        hoa_name = row.get(self.COLUMN_MAPPING["hoa_name"].lower(), "").strip()
        if hoa_name:
            return self._find_homeowner_association_by_name(
                hoa_name, row_number, skip_hoa_api=self.skip_hoa_api
            )
        return None

    def _parse_course_date(
        self, date_string: str, row_number: int
    ) -> Optional[datetime]:
        """
        Parse course date. Supports most common date formats and strips optional time component.
        Returns datetime object or None if parsing fails.
        """
        if not date_string or not date_string.strip():
            return None

        date_string = date_string.strip()

        # Remove time component if present
        if " " in date_string:
            date_part = date_string.split(" ")[0]
        else:
            date_part = date_string

        # Allowed date formats
        formats = [
            "%d/%m/%Y",  # DD/MM/YYYY or D/M/YYYY
            "%d/%m/%y",  # DD/MM/YY or D/M/YY
            "%d-%m-%Y",  # DD-MM-YYYY or D-M-YYYY
            "%d-%m-%y",  # DD-MM-YY or D-M-YY
        ]

        for format in formats:
            try:
                return datetime.strptime(date_part, format)
            except ValueError:
                continue

        return None

    def _process_row(self, row: Dict[str, str], row_number: int) -> bool:
        """
        Process a single course participant row and return a boolean indicating if the row was processed successfully.
        """
        email = row.get(self.COLUMN_MAPPING["contact_email"].lower(), "").strip()

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

        fullname = (
            row.get(self.COLUMN_MAPPING["contact_fullname"].lower(), "").strip() or ""
        )

        # Parse course date - required field
        course_date_str = row.get(
            self.COLUMN_MAPPING["course_date"].lower(), ""
        ).strip()
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
                f"Ongeldige cursusdatum: '{course_date_str}'. Mogelijke formaten: DD/MM/YYYY, DD/MM/YY, D/M/YYYY, D/M/YY, DD-MM-YYYY, DD-MM-YY, D-M-YYYY, D-M-YY",
            )
            return False

        # Find `HomeownerAssociation`
        hoa_name = row.get(self.COLUMN_MAPPING["hoa_name"].lower(), "").strip()
        hoa = self._find_homeowner_association(row, row_number)
        if not hoa:
            self._add_error(
                row_number,
                None,
                f"Kon vve niet vinden voor '{hoa_name}'",
            )
            return False

        # Get optional fields
        phone = row.get(self.COLUMN_MAPPING["contact_phone"].lower(), "").strip()
        role = row.get(self.COLUMN_MAPPING["contact_role"].lower(), "").strip()

        try:
            if self.dry_run:
                self._add_message(
                    f"Rij {row_number}: [DRY RUN] Zou contact {email} aanmaken/bijwerken "
                    f"voor vve {hoa.name} met cursusdatum {course_date_str}"
                )
            else:
                with transaction.atomic():
                    contact = Contact.objects.filter(
                        email__iexact=email,
                        homeowner_association=hoa,
                        fullname__iexact=fullname,
                    ).first()

                    if contact:
                        # Update existing contact
                        contact.phone = phone or contact.phone
                        contact.role = role or contact.role or self.DEFAULT_ROLE
                        contact.course_date = course_date.date()
                        contact.save()
                    else:
                        # Create new contact
                        contact = Contact.objects.create(
                            email=email,
                            fullname=fullname,
                            phone=phone,
                            role=role or self.DEFAULT_ROLE,
                            homeowner_association=hoa,
                            course_date=course_date.date(),
                        )

            return True

        except Exception as e:
            self._add_error(
                row_number, None, f"Fout bij het opslaan van contact: {str(e)}"
            )
            return False
