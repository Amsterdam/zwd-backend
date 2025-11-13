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
        "contact_is_active": "Gestopt",
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

        # Try to find by `Statutaire Naam` (HomeownerAssociation `name`, exact match)
        if hoa_name:
            try:
                hoa = HomeownerAssociation.objects.filter(name=hoa_name).first()
                if hoa:
                    return hoa

                # HOA not found in database, try to fetch from DSO API and create it
                if not self.dry_run and not self.skip_hoa_api:
                    try:
                        # Create a temporary instance to use the `_get_hoa_data` method
                        temp_hoa = HomeownerAssociation()
                        data = temp_hoa._get_hoa_data(hoa_name)

                        # Check if we got valid data (`response` should not be empty)
                        if not data.get("response"):
                            raise ValueError("No data returned from external API")

                        # Create the HOA with data from external API
                        with transaction.atomic():
                            hoa = HomeownerAssociation.objects.create(
                                name=data["hoa_name"],
                                build_year=data["build_year"],
                                number_of_apartments=data["number_of_apartments"],
                                district=data["district"],
                                neighborhood=data["neighborhood"],
                                wijk=data["wijk"],
                                zip_code=data["zip_code"],
                                monument_status=data["monument_status"],
                                ligt_in_beschermd_gebied=data[
                                    "ligt_in_beschermd_gebied"
                                ],
                                beschermd_stadsdorpsgezicht=data[
                                    "beschermd_stadsdorpsgezicht"
                                ],
                                kvk_nummer=data["kvk_nummer"],
                            )
                            # Create ownerships from the API response
                            temp_hoa._create_ownerships(data["response"], hoa)

                        self._add_message(
                            f"Row {row_number}: Created new HOA '{hoa_name}' from external API"
                        )
                        return hoa
                    except (IndexError, KeyError, ValueError) as e:
                        # API returned empty or invalid data
                        self._add_warning(
                            f"Row {row_number}: Could not fetch HOA data from external API for '{hoa_name}': {str(e)}"
                        )
                    except Exception as e:
                        # Other API or creation errors
                        self._add_warning(
                            f"Row {row_number}: Error creating HOA '{hoa_name}' from external API: {str(e)}"
                        )
                else:
                    # In dry-run mode, try to fetch data but don't create (unless `skip_hoa_api` is set)
                    if not self.skip_hoa_api:
                        try:
                            temp_hoa = HomeownerAssociation()
                            data = temp_hoa._get_hoa_data(hoa_name)
                            if data.get("response"):
                                self._add_message(
                                    f"Row {row_number}: [DRY RUN] Would create new HOA '{hoa_name}' from external API"
                                )
                            else:
                                self._add_warning(
                                    f"Row {row_number}: [DRY RUN] No data available from external API for '{hoa_name}'"
                                )
                        except Exception as e:
                            self._add_warning(
                                f"Row {row_number}: [DRY RUN] Could not fetch HOA data from external API for '{hoa_name}': {str(e)}"
                            )
                    # Return None in dry-run since we're not actually creating it
                    return None
            except Exception as e:
                self._add_warning(
                    f"Row {row_number}: Error looking up HOA by name '{hoa_name}': {str(e)}"
                )

        return None

    def _parse_is_active(self, gestopt_value: str) -> bool:
        """
        Parse `Gestopt` field to boolean.
        """
        gestopt = gestopt_value.strip().lower()
        return gestopt != "ja"

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
        gestopt = row.get(self.COLUMN_MAPPING["contact_is_active"], "").strip()
        is_active = self._parse_is_active(gestopt)

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
                            homeowner_association=hoa,
                        )

            return True

        except Exception as e:
            self._add_error(row_number, None, f"Error saving contact: {str(e)}")
            return False
