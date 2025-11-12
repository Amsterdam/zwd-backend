from typing import Dict, Optional
from django.db import transaction
from apps.cases.models import Case
from apps.homeownerassociation.models import Contact, HomeownerAssociation
from .base import BaseImporter


class ContactImporter(BaseImporter):
    """Importer for contact CSV files"""

    REQUIRED_COLUMNS_SORTED = [
        "ZWD",  # prefixed_dossier_id
        "Vnummer",  # Unused: vestigingsnummer?
        "Statutaire Naam",  # hoa_name
        "Kontaktpersoon",  # fullname
        "Mailadres",  # email
        "Gestopt",  # is_active
    ]

    def __init__(self, dry_run: bool = False):
        super().__init__(self.REQUIRED_COLUMNS_SORTED, dry_run=dry_run)

    def _find_homeowner_association(
        self, row: Dict[str, str], row_number: int
    ) -> Optional[HomeownerAssociation]:
        """
        Find HomeownerAssociation using ZWD (case prefixed_dossier_id) or Statutaire Naam

        Args:
            row: CSV row data
            row_number: Row number for error reporting

        Returns:
            HomeownerAssociation instance or None if not found
        """
        prefixed_dossier_id = row.get(self.REQUIRED_COLUMNS_SORTED[0], "").strip()
        hoa_name = row.get(self.REQUIRED_COLUMNS_SORTED[2], "").strip()

        # Try to find by ZWD (case prefixed_dossier_id) first
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

        # Fallback: try to find by Statutaire Naam (exact match)
        if hoa_name:
            try:
                hoa = HomeownerAssociation.objects.filter(name=hoa_name).first()
                if hoa:
                    return hoa
            except Exception as e:
                self._add_warning(
                    f"Row {row_number}: Error looking up HOA by name '{hoa_name}': {str(e)}"
                )

        return None

    def _parse_is_active(self, gestopt_value: str) -> bool:
        """
        Parse `Gestopt` field to boolean

        Args:
            gestopt_value: Value from 'Gestopt' column

        Returns:
            True if active (Gestopt = "Nee") or unset/empty, False if stopped (Gestopt = "Ja")
        """
        gestopt = gestopt_value.strip().lower()
        return gestopt != "ja"

    def _process_row(self, row: Dict[str, str], row_number: int) -> bool:
        """
        Process a single contact row

        Args:
            row: Dictionary of column name -> value
            row_number: Row number (for error reporting)

        Returns:
            True if row was processed successfully, False if skipped
        """
        # Extract and validate fields
        email_raw = row.get(self.REQUIRED_COLUMNS_SORTED[4], "").strip()
        email = self._normalize_email(email_raw)

        # Validate email
        if not email:
            self._add_error(
                row_number, self.REQUIRED_COLUMNS_SORTED[4], "Email address is required"
            )
            return False

        if not self._validate_email(email):
            self._add_error(
                row_number,
                self.REQUIRED_COLUMNS_SORTED[4],
                f"Invalid email format: {email_raw}",
            )
            return False

        # Get fullname
        fullname = row.get(self.REQUIRED_COLUMNS_SORTED[3], "").strip()
        if not fullname:
            self._add_error(
                row_number,
                self.REQUIRED_COLUMNS_SORTED[3],
                "Contact person name is required",
            )
            return False

        # Get `is_active` from `Gestopt` field
        gestopt = row.get(self.REQUIRED_COLUMNS_SORTED[5], "").strip()
        is_active = self._parse_is_active(gestopt)

        # Find `HomeownerAssociation`
        hoa = self._find_homeowner_association(row, row_number)
        if not hoa:
            self._add_error(
                row_number,
                None,
                "Could not find homeowner association. Check ZWD and Statutaire Naam values.",
            )
            return False

        # Set defaults, since these are not in the CSV
        role = "Geïmporteerd contact"
        phone = ""

        try:
            if self.dry_run:
                # In dry-run mode, just validate without saving
                self._add_warning(
                    f"Row {row_number}: [DRY RUN] Would create/update contact {email} for HOA {hoa.name}"
                )
            else:
                with transaction.atomic():
                    # Find existing contact by email (case-insensitive)
                    contact = Contact.objects.filter(email__iexact=email).first()

                    if contact:
                        # Update existing contact
                        contact.fullname = fullname
                        contact.phone = (
                            contact.phone or phone
                        )  # Leave as is, if present
                        contact.role = contact.role or role  # Leave as is, if present
                        contact.is_active = is_active
                        contact.save()
                    else:
                        # Create new contact
                        contact = Contact.objects.create(
                            email=email,
                            fullname=fullname,
                            phone=phone,
                            role=role,
                            is_active=is_active,
                        )

                    # Add HOA relationship (ManyToMany, so this is safe to call multiple times)
                    contact.homeowner_associations.add(hoa)

            return True

        except Exception as e:
            self._add_error(row_number, None, f"Error saving contact: {str(e)}")
            return False
