import csv
import io
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import transaction


class ImportError(Exception):
    """Base exception for import errors"""


class RowError:
    def __init__(self, row_number: int, field: Optional[str], message: str):
        self.row_number = row_number
        self.field = field
        self.message = message

    def __str__(self):
        if self.field:
            return f"Rij {self.row_number}, veld '{self.field}': {self.message}"
        return f"Rij {self.row_number}: {self.message}"


class ImportResult:
    def __init__(self):
        self.failed_rows: Set[int] = set()
        self.total_rows = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.errors: List[RowError] = []
        self.warnings: List[str] = []
        self.messages: List[str] = []

    def add_error(self, row_number: int, field: Optional[str], message: str):
        """Add an error to the result"""
        self.errors.append(RowError(row_number, field, message))
        if row_number not in self.failed_rows:
            self.failed_rows.add(row_number)
            self.failed += 1

    def add_warning(self, message: str):
        """Add a warning to the result (concerning but not fatal)"""
        self.warnings.append(message)

    def add_message(self, message: str):
        """Add an informational message to the result"""
        self.messages.append(message)

    def __str__(self):
        return (
            f"Import voltooid: {self.successful} succesvol, "
            f"{self.failed} mislukt, {self.skipped} overgeslagen van {self.total_rows} totaal aantal rijen"
        )


class BaseImporter(ABC):
    def __init__(self, required_columns: List[str], dry_run: bool = False):
        """
        Initialize the importer
        """
        self.required_columns = required_columns
        self.dry_run = dry_run
        self.result = ImportResult()
        self.email_validator = EmailValidator()

    def import_file(self, file_path: str) -> ImportResult:
        """
        Main import method that processes the CSV file and returns a result object.
        """
        self.result = ImportResult()

        try:
            headers, rows = self._read_csv(file_path)
            self._validate_headers(headers)

            # Process each row
            self.result.total_rows = len(rows)

            # Loop over rows, and start at 2 (since row 1 is the header)
            for idx, row in enumerate(rows, start=2):
                try:
                    errors_before = len(self.result.errors)
                    processed = self._process_row(row, idx)
                    errors_after = len(self.result.errors)

                    if processed:
                        self.result.successful += 1
                    else:
                        if errors_after == errors_before:
                            self.result.skipped += 1
                except Exception as e:
                    self.result.add_error(idx, None, str(e))

        except ImportError as e:
            self.result.add_error(0, None, str(e))

        return self.result

    def _detect_encoding(self, file_path: str) -> str:
        """
        Detect file encoding, trying UTF-8 first, then Windows-1252.
        """
        encodings = ["utf-8-sig", "utf-8", "windows-1252", "latin-1"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    f.read()
                return encoding
            except (UnicodeDecodeError, UnicodeError):
                continue

        # Default to utf-8 if all fail
        return "utf-8"

    def _detect_delimiter(self, first_line: str) -> Optional[str]:
        """
        Detect CSV delimiter by checking the first line (semicolon or comma).
        Returns None if no delimiter is found (single-column file).
        """
        # Count semicolons and commas in the first line
        semicolon_count = first_line.count(";")
        comma_count = first_line.count(",")

        # If no delimiter found, return None (single-column file)
        if semicolon_count == 0 and comma_count == 0:
            return None

        # Use semicolon if it appears more frequently, otherwise default to comma
        if semicolon_count > comma_count:
            return ";"
        return ","

    def _read_csv(self, file_path: str) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        Read and parse CSV file
        We strip whitespace from all keys and values, and handle None values to avoid errors.
        """
        encoding = self._detect_encoding(file_path)

        try:
            with open(file_path, "r", encoding=encoding) as f:
                # Try to detect if there's a BOM
                content = f.read()
                # Remove BOM if present
                if content.startswith("\ufeff"):
                    content = content[1:]

                # Detect delimiter from first line
                first_line = content.split("\n")[0] if content else ""
                delimiter = self._detect_delimiter(first_line)

                # Handle single-column file (no delimiter)
                if delimiter is None:
                    # For single-column files, read line by line and handle quotes manually
                    # Since there's no delimiter, we can't use csv.reader (it defaults to comma)
                    lines_raw = content.strip().split("\n")
                    lines = []
                    for line in lines_raw:
                        line = line.strip()
                        if not line:
                            continue
                        # Handle quoted values: remove surrounding quotes and unescape internal quotes
                        if line.startswith('"') and line.endswith('"'):
                            # Remove surrounding quotes
                            line = line[1:-1]
                            # Replace escaped quotes (double quotes) with single quotes
                            line = line.replace('""', '"')
                        lines.append(line)

                    if not lines:
                        raise ImportError("CSV-bestand is leeg")

                    # First line is the header
                    header = lines[0].strip()
                    if not header:
                        raise ImportError("CSV-bestand heeft geen headers")

                    headers = [header]
                    rows = []
                    # Process remaining lines as single-column values
                    for line in lines[1:]:
                        cleaned_row = {header: line.strip()}
                        rows.append(cleaned_row)
                else:
                    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
                    headers = reader.fieldnames

                    if not headers:
                        raise ImportError("CSV-bestand heeft geen headers")

                    # Normalize headers: strip whitespace and handle None values
                    headers = [
                        h.strip() if h and isinstance(h, str) else "" for h in headers
                    ]
                    reader.fieldnames = headers

                    rows = []
                    for row in reader:
                        # Strip whitespace from all keys and values, handle None values
                        cleaned_row = {}
                        for k, v in row.items():
                            # Handle None keys
                            key = k.strip() if k and isinstance(k, str) else ""
                            # Handle None values
                            value = v.strip() if v and isinstance(v, str) else ""
                            cleaned_row[key] = value
                        rows.append(cleaned_row)

                return headers, rows

        except FileNotFoundError:
            raise ImportError(f"Bestand niet gevonden: {file_path}")
        except ImportError:
            # Re-raise ImportError as-is
            raise
        except Exception as e:
            raise ImportError(f"Fout bij het lezen van CSV-bestand: {str(e)}")

    def _validate_headers(self, headers: List[str]) -> None:
        """
        Validate that all required columns are present.
        """
        missing_columns = []
        for col in self.required_columns:
            if col not in headers:
                missing_columns.append(col)

        if missing_columns:
            raise ImportError(
                f"Ontbrekende verplichte kolommen: {', '.join(f'‘{col}’' for col in missing_columns)}. "
                f"Gevonden kolommen: {', '.join(f'‘{col}’' for col in headers)}"
            )

    def _validate_email(self, email: str) -> bool:
        """
        Validate email format using Django's EmailValidator.
        """
        if not email:
            return False

        try:
            self.email_validator(email)
            return True
        except ValidationError:
            return False

    @abstractmethod
    def _process_row(self, row: Dict[str, str], row_number: int) -> bool:
        """
        Abstract method to process a single row from the CSV and return a boolean indicating if the row was processed successfully.
        """

    def _add_error(self, row_number: int, field: Optional[str], message: str):
        self.result.add_error(row_number, field, message)

    def _add_warning(self, message: str):
        self.result.add_warning(message)

    def _add_message(self, message: str):
        self.result.add_message(message)

    def _find_homeowner_association_by_name(
        self,
        hoa_name: str,
        row_number: int,
        skip_hoa_api: bool = False,
    ) -> Optional["HomeownerAssociation"]:
        """
        Find HomeownerAssociation by exact name match with optional DSO API fallback.

        Args:
            hoa_name: The HOA name to look up (e.g. a 'Statutaire Naam' column)
            row_number: The current row number for returning error/warning messages
            skip_hoa_api: If True, skip fetching from DSO API even if HOA not found

        Returns:
            HomeownerAssociation instance if found/created, None otherwise
        """
        if not hoa_name:
            return None

        try:
            # Import here to avoid circular imports
            from apps.homeownerassociation.models import HomeownerAssociation

            # Try exact name match first
            hoa = HomeownerAssociation.objects.filter(name=hoa_name).first()
            if hoa:
                return hoa

            # HOA not found in database, try to fetch from DSO API and create it
            if not self.dry_run and not skip_hoa_api:
                try:

                    # Create a temporary instance to use the `_get_hoa_data` method
                    temp_hoa = HomeownerAssociation()
                    data = temp_hoa._get_hoa_data(hoa_name)

                    # Check if we got valid data (`response` should not be empty)
                    if not data.get("response"):
                        raise ValueError("Geen data teruggekregen van externe DSO API")

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
                            ligt_in_beschermd_gebied=data["ligt_in_beschermd_gebied"],
                            beschermd_stadsdorpsgezicht=data[
                                "beschermd_stadsdorpsgezicht"
                            ],
                            kvk_nummer=data["kvk_nummer"],
                        )
                        # Create ownerships from the API response
                        temp_hoa._create_ownerships(data["response"], hoa)

                    self._add_message(
                        f"Rij {row_number}: Nieuwe vve '{hoa_name}' aangemaakt vanuit externe API"
                    )
                    return hoa
                except (IndexError, KeyError, ValueError) as e:
                    # API returned empty or invalid data
                    self._add_warning(
                        f"Rij {row_number}: Kon vve-data niet ophalen van externe API voor '{hoa_name}': {str(e)}"
                    )
                except Exception as e:
                    # Other API or creation errors
                    self._add_warning(
                        f"Rij {row_number}: Fout bij het aanmaken van vve '{hoa_name}' vanuit externe API: {str(e)}"
                    )
            else:
                # In dry-run mode, try to fetch data but don't create (unless `skip_hoa_api` is set)
                if not skip_hoa_api:
                    try:
                        temp_hoa = HomeownerAssociation()
                        data = temp_hoa._get_hoa_data(hoa_name)
                        if data.get("response"):
                            self._add_message(
                                f"Rij {row_number}: [DRY RUN] Zou nieuwe VvE '{hoa_name}' aanmaken vanuit externe API"
                            )

                            class HomeownerAssociationMock:
                                def __init__(self, name: str):
                                    self.name = name
                                    self.pk = None

                            return HomeownerAssociationMock(hoa_name)
                        else:
                            self._add_warning(
                                f"Rij {row_number}: [DRY RUN] Geen data beschikbaar van externe API voor '{hoa_name}'"
                            )
                    except Exception as e:
                        self._add_warning(
                            f"Rij {row_number}: [DRY RUN] Kon vve-data niet ophalen van externe API voor '{hoa_name}': {str(e)}"
                        )
                # Return None in dry-run since we're not actually creating it
                return None
        except Exception as e:
            self._add_warning(
                f"Rij {row_number}: Fout bij het opzoeken van vve op naam '{hoa_name}': {str(e)}"
            )

        return None
