from datetime import datetime
from typing import Dict, Optional
from django.db import transaction
from apps.homeownerassociation.models import (
    HomeownerAssociation,
    HomeownerAssociationCommunicationNote,
)
from .base import BaseImporter


class LetterImporter(BaseImporter):
    """
    Importer for sent letter CSV files.
    Creates a single `HomeownerAssociationCommunicationNote` for each matched homeowner association.
    """

    COLUMNS_REQUIRED = [
        "vve",
    ]

    COLUMN_MAPPING = {
        "hoa_name": "vve",
    }

    def __init__(
        self,
        date: datetime,
        description: str,
        author_name: str,
        dry_run: bool = False,
        skip_hoa_api: bool = False,
    ):
        super().__init__(self.COLUMNS_REQUIRED, dry_run=dry_run)
        self.date = date
        self.description = description
        self.author_name = author_name
        self.skip_hoa_api = skip_hoa_api
        self.processed_hoa_names: set[str] = set()

    def _find_homeowner_association(
        self, row: Dict[str, str], row_number: int
    ) -> Optional[HomeownerAssociation]:
        """
        Find HomeownerAssociation by exact name match (`Statutaire Naam` → `HomeownerAssociation.name`) with optional DSO API fallback.
        """
        hoa_name = row.get(self.COLUMN_MAPPING["hoa_name"], "").strip()
        return self._find_homeowner_association_by_name(
            hoa_name, row_number, skip_hoa_api=self.skip_hoa_api
        )

    def _process_row(self, row: Dict[str, str], row_number: int) -> bool:
        """
        Process a single letter row and return a boolean indicating if the row was processed successfully.
        """
        # Find `HomeownerAssociation`
        hoa_name = row.get(self.COLUMN_MAPPING["hoa_name"], "").strip()

        # Check for duplicate exact matches of HOA names in previous rows (deduplicate exact matches)
        if hoa_name in self.processed_hoa_names:
            self._add_message(
                f"Rij {row_number}: Dubbele vve '{hoa_name}' overgeslagen (al verwerkt in eerdere rijen)"
            )
            return False

        # Check database first before attempting API fetch
        hoa = HomeownerAssociation.objects.filter(name=hoa_name).first()

        # If not in database, try to find/create via API (only if not already attempted)
        if not hoa:
            hoa = self._find_homeowner_association(row, row_number)
            if not hoa:
                # Mark as processed to avoid retrying API fetch for duplicates
                self.processed_hoa_names.add(hoa_name)
                self._add_error(
                    row_number,
                    None,
                    f"Kon vve niet vinden voor '{hoa_name}'",
                )
                return False

        # Check for already imported communication notes (e.g. if the script is run multiple times).
        # We're assuming (for now) that a communication note with these criteria would be unique:
        # - Same homeowner association
        # - Same date (ignoring time, e.g. 2025-11-26 is the same as 2025-11-26 08:00:00)
        # - Flag `is_imported` is set `True`
        existing_note = HomeownerAssociationCommunicationNote.objects.filter(
            homeowner_association=hoa,
            date__date=self.date.date(),
            is_imported=True,
        ).exists()

        if existing_note:
            if self.dry_run:
                self._add_message(
                    f"Rij {row_number}: [DRY RUN] Zou dubbele geïmporteerde contactmelding voor vve '{hoa.name}' overslaan "
                    f"(bestaat al voor datum {self.date.strftime('%d-%m-%Y')})"
                )
            else:
                self._add_message(
                    f"Rij {row_number}: Dubbele import van contactmelding overgeslagen voor vve '{hoa.name}' "
                    f"(bestaat al voor datum {self.date.strftime('%d-%m-%Y')})"
                )
            # Mark this HOA name as processed to avoid duplicate messages
            self.processed_hoa_names.add(hoa_name)
            return False

        try:
            if self.dry_run:
                self._add_message(
                    f"Rij {row_number}: [DRY RUN] Zou contactmelding aanmaken voor vve '{hoa.name}' "
                    f"met datum {self.date}, auteur '{self.author_name}', en beschrijving '{self.description}'"
                )
            else:
                with transaction.atomic():
                    HomeownerAssociationCommunicationNote.objects.create(
                        homeowner_association=hoa,
                        note=self.description,
                        author_name=self.author_name,
                        date=self.date,
                        author=None,
                        is_imported=True,
                    )

            # Mark this HOA name as processed
            self.processed_hoa_names.add(hoa_name)
            return True

        except Exception as e:
            self._add_error(
                row_number, None, f"Fout bij het opslaan van contactmelding: {str(e)}"
            )
            return False
