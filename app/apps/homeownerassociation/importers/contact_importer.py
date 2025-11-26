from typing import Dict, Optional
from django.db import transaction
from apps.cases.models import Case
from apps.homeownerassociation.models import Contact, HomeownerAssociation
from .base import BaseImporter


class ContactImporter(BaseImporter):
    """Importer for contact CSV files"""

    COLUMNS_REQUIRED = [
        "ZWD",
        "Vnummer",
        "Statutaire Naam",
        "Mailadres",
    ]

    COLUMN_MAPPING = {
        "case_prefixed_dossier_id": "ZWD",
        "case_legacy_id": "Vnummer",
        "hoa_name": "Statutaire Naam",
        "contact_fullname": "Kontaktpersoon",
        "contact_email": "Mailadres",
        "contact_is_active": "Gestopt",  # Not used for now
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
                        f"Row {row_number}: Case {prefixed_dossier_id} found but has no homeowner_association"
                    )
            except Exception as e:
                self._add_warning(
                    f"Row {row_number}: Error looking up case {prefixed_dossier_id}: {str(e)}"
                )

        # Try to find by `Vnummer` (Case `legacy_id`)
        if legacy_id and legacy_id != "0":
            try:
                case = Case.objects.filter(legacy_id__iexact=legacy_id).first()
                if case and case.homeowner_association:
                    return case.homeowner_association
            except Exception as e:
                self._add_warning(
                    f"Row {row_number}: Error looking up case {legacy_id}: {str(e)}"
                )

        # Try to find by `Statutaire Naam` (HomeownerAssociation `name`, exact match with DSO API fallback)
        if hoa_name:
            hoa = self._find_homeowner_association_by_name(
                hoa_name, row_number, skip_hoa_api=self.skip_hoa_api
            )
            if hoa:
                return hoa

        return None

    def _process_row(self, row: Dict[str, str], row_number: int) -> bool:
        """
        Process a single contact row and return a boolean indicating if the row was processed successfully.
        """
        email = row.get(self.COLUMN_MAPPING["contact_email"], "").strip()

        if not email:
            self._add_error(
                row_number,
                self.COLUMN_MAPPING["contact_email"],
                "Email address is required",
            )
            return False

        if not self._validate_email(email):
            self._add_error(
                row_number,
                self.COLUMN_MAPPING["contact_email"],
                f"Invalid email format: {email}",
            )
            return False

        fullname = row.get(self.COLUMN_MAPPING["contact_fullname"], "").strip() or ""

        # Find `HomeownerAssociation`
        hoa_name = row.get(self.COLUMN_MAPPING["hoa_name"], "").strip()
        hoa = self._find_homeowner_association(row, row_number)
        if not hoa:
            self._add_error(
                row_number,
                None,
                f"Could not find homeowner association for '{hoa_name}'",
            )
            return False

        # Set defaults, since these are not in the CSV or optional
        role = "Geïmporteerd contact"
        phone = ""

        try:
            if self.dry_run:
                self._add_message(
                    f"Row {row_number}: [DRY RUN] Would create/update contact {email} for HOA {hoa.name}"
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
                        contact.phone = contact.phone or phone
                        contact.role = contact.role or role
                        contact.save()
                    else:
                        # Create new contact
                        contact = Contact.objects.create(
                            email=email,
                            fullname=fullname,
                            phone=phone,
                            role=role,
                            homeowner_association=hoa,
                        )

            return True

        except Exception as e:
            self._add_error(row_number, None, f"Error saving contact: {str(e)}")
            return False
