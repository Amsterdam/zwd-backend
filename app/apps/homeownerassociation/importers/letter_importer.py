from datetime import datetime
from typing import Dict, Optional, Set
from django.db import transaction
from apps.homeownerassociation.models import (
    HomeownerAssociation,
    HomeownerAssociationCommunicationNote,
)
from .base import BaseImporter, ImportResult


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

        self._processed_hoa_names: set[str] = set()
        self._existing_hoa_cache: Dict[str, Optional[HomeownerAssociation]] = {}
        self._existing_notes_cache: Set[int] = set()
        self._notes_to_create: list[HomeownerAssociationCommunicationNote] = []

    def import_file(self, file_path: str) -> ImportResult:
        """
        Override `BaseImporter` to cater for bulk prefetching and batch creation.
        """
        self.result = ImportResult()

        try:
            headers, rows = self._read_csv(file_path)
            self._validate_headers(headers)
            self.result.total_rows = len(rows)

            unique_hoa_names = {
                row.get(self.COLUMN_MAPPING["hoa_name"].lower(), "").strip()
                for row in rows
                if row.get(self.COLUMN_MAPPING["hoa_name"].lower(), "").strip()
            }
            self._prefetch_hoas(unique_hoa_names)

            hoa_ids = {hoa.id for hoa in self._existing_hoa_cache.values() if hoa}
            if not self.dry_run:
                self._prefetch_existing_notes(hoa_ids)

            for idx, row in enumerate(rows, start=2):
                try:
                    errors_before = len(self.result.errors)
                    processed = self._process_row(row, idx)
                    errors_after = len(self.result.errors)

                    if processed:
                        self.result.successful += 1
                    elif errors_after == errors_before:
                        self.result.skipped += 1
                except Exception as e:
                    self.result.add_error(idx, None, str(e))

            if not self.dry_run and self._notes_to_create:
                try:
                    with transaction.atomic():
                        HomeownerAssociationCommunicationNote.objects.bulk_create(
                            self._notes_to_create, batch_size=500
                        )
                except Exception as e:
                    self.result.add_warning(
                        f"Fout bij het aanmaken van contactmeldingen: {str(e)}"
                    )

        except ImportError as e:
            self.result.add_error(0, None, str(e))

        return self.result

    def _find_homeowner_association(
        self, row: Dict[str, str], row_number: int
    ) -> Optional[HomeownerAssociation]:
        """
        Find HomeownerAssociation by exact name match (`Statutaire Naam` → `HomeownerAssociation.name`) with optional DSO API fallback.
        """
        hoa_name = row.get(self.COLUMN_MAPPING["hoa_name"].lower(), "").strip()
        return self._find_homeowner_association_by_name(
            hoa_name, row_number, skip_hoa_api=self.skip_hoa_api
        )

    def _prefetch_hoas(self, hoa_names: Set[str]) -> None:
        """
        Prefetch all `HomeownerAssociation`s by name in a single query.
        """
        names_to_fetch = {
            name for name in hoa_names if name and name not in self._existing_hoa_cache
        }
        if not names_to_fetch:
            return

        for hoa in HomeownerAssociation.objects.filter(name__in=names_to_fetch):
            self._existing_hoa_cache[hoa.name] = hoa

    def _prefetch_existing_notes(self, hoa_ids: Set[int]) -> None:
        """
        Prefetch all existing communication notes by homeowner association ID, date and `is_imported` flag.
        """
        if not hoa_ids:
            return

        self._existing_notes_cache.update(
            HomeownerAssociationCommunicationNote.objects.filter(
                homeowner_association_id__in=hoa_ids,
                date__date=self.date.date(),
                is_imported=True,
            ).values_list("homeowner_association_id", flat=True)
        )

    def _process_row(self, row: Dict[str, str], row_number: int) -> bool:
        """
        Process a single letter row and return a boolean indicating if the row was processed successfully.
        """
        # Find `HomeownerAssociation`
        hoa_name = row.get(self.COLUMN_MAPPING["hoa_name"].lower(), "").strip()

        # Check for duplicate exact matches of HOA names in previous rows (deduplicate exact matches)
        if hoa_name in self._processed_hoa_names:
            self._add_message(
                f"Rij {row_number}: Dubbele vve '{hoa_name}' overgeslagen (al verwerkt in eerdere rijen)"
            )
            return False

        # Check existing HOAs first before attempting API fetch
        hoa = self._existing_hoa_cache.get(hoa_name)

        # If not in database, try to find/create via API (only if not already attempted)
        if not hoa:
            hoa = self._find_homeowner_association(row, row_number)
            if hoa:
                self._existing_hoa_cache[hoa_name] = hoa
            else:
                # Mark as processed to avoid retrying API fetch for duplicates
                self._processed_hoa_names.add(hoa_name)
                self._add_error(
                    row_number,
                    self.COLUMN_MAPPING["hoa_name"],
                    f"Kon vve niet vinden voor '{hoa_name}'",
                )
                return False

        # Check for already imported communication notes (e.g. if the script is run multiple times).
        # We're assuming (for now) that a communication note with these criteria would be unique:
        # - Same homeowner association
        # - Same date (ignoring time, e.g. 2025-11-26 is the same as 2025-11-26 08:00:00)
        # - Flag `is_imported` is set `True`
        existing_note = False
        if not self.dry_run or isinstance(hoa, HomeownerAssociation):
            existing_note = hoa.id in self._existing_notes_cache

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
            self._processed_hoa_names.add(hoa_name)
            return False

        try:
            if self.dry_run:
                self._add_message(
                    f"Rij {row_number}: [DRY RUN] Zou contactmelding aanmaken voor vve '{hoa.name}' "
                    f"met datum {self.date}, auteur '{self.author_name}', en beschrijving '{self.description}'"
                )
            else:
                self._notes_to_create.append(
                    HomeownerAssociationCommunicationNote(
                        homeowner_association=hoa,
                        note=self.description,
                        author_name=self.author_name,
                        date=self.date,
                        author=None,
                        is_imported=True,
                    )
                )

            # Mark this HOA name as processed
            self._processed_hoa_names.add(hoa_name)
            return True

        except Exception as e:
            self._add_error(
                row_number, None, f"Fout bij het opslaan van contactmelding: {str(e)}"
            )
            return False
