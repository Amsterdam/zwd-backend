from datetime import datetime
from typing import Dict, Optional, TYPE_CHECKING
from django.db import transaction
from apps.homeownerassociation.models import HomeownerAssociationCommunicationNote
from .base import BaseImporter

if TYPE_CHECKING:
    from apps.homeownerassociation.models import HomeownerAssociation


class LetterImporter(BaseImporter):
    """Importer for letter CSV files"""

    COLUMNS_REQUIRED = [
        "Statutaire Naam",
    ]

    COLUMN_MAPPING = {
        "hoa_name": "Statutaire Naam",
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
    ) -> Optional["HomeownerAssociation"]:
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

        # Check for duplicate HOA names (deduplicate exact matches)
        if hoa_name in self.processed_hoa_names:
            self._add_message(
                f"Row {row_number}: Skipping duplicate HOA '{hoa_name}' (already processed)"
            )
            return False

        hoa = self._find_homeowner_association(row, row_number)
        if not hoa:
            self._add_error(
                row_number,
                None,
                f"Could not find homeowner association for '{hoa_name}'",
            )
            return False

        try:
            if self.dry_run:
                self._add_message(
                    f"Row {row_number}: [DRY RUN] Would create communication note for HOA {hoa.name} "
                    f"with date {self.date}, author '{self.author_name}', and description '{self.description}'"
                )
            else:
                with transaction.atomic():
                    HomeownerAssociationCommunicationNote.objects.create(
                        homeowner_association=hoa,
                        note=self.description,
                        author_name=self.author_name,
                        date=self.date,
                        author=None,
                    )

            # Mark this HOA name as processed
            self.processed_hoa_names.add(hoa_name)
            return True

        except Exception as e:
            self._add_error(
                row_number, None, f"Error saving communication note: {str(e)}"
            )
            return False
