import csv
import io
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator


class ImportError(Exception):
    """Base exception for import errors"""


class RowError:
    def __init__(self, row_number: int, field: Optional[str], message: str):
        self.row_number = row_number
        self.field = field
        self.message = message

    def __str__(self):
        if self.field:
            return f"Row {self.row_number}, field '{self.field}': {self.message}"
        return f"Row {self.row_number}: {self.message}"


class ImportResult:
    def __init__(self):
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
        self.failed += 1

    def add_warning(self, message: str):
        """Add a warning to the result (concerning but not fatal)"""
        self.warnings.append(message)

    def add_message(self, message: str):
        """Add an informational message to the result"""
        self.messages.append(message)

    def __str__(self):
        return (
            f"Import completed: {self.successful} successful, "
            f"{self.failed} failed, {self.skipped} skipped out of {self.total_rows} total rows"
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

    def _detect_delimiter(self, first_line: str) -> str:
        """
        Detect CSV delimiter by checking the first line (semicolon or comma).
        """
        # Count semicolons and commas in the first line
        semicolon_count = first_line.count(";")
        comma_count = first_line.count(",")

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

                reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
                headers = reader.fieldnames

                if not headers:
                    raise ImportError("CSV file has no headers")

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
            raise ImportError(f"File not found: {file_path}")
        except ImportError:
            # Re-raise ImportError as-is
            raise
        except Exception as e:
            raise ImportError(f"Error reading CSV file: {str(e)}")

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
                f"Missing required columns: {', '.join(missing_columns)}. "
                f"Found columns: {', '.join(headers)}"
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

    def import_file(self, file_path: str) -> ImportResult:
        """
        Main import method that processes the CSV file and returns a result object.
        """
        try:
            headers, rows = self._read_csv(file_path)
            self._validate_headers(headers)

            # Process each row
            self.result.total_rows = len(rows)

            # Loop over rows, and start at 2 (since row 1 is the header)
            for idx, row in enumerate(rows, start=2):
                try:
                    if self._process_row(row, idx):
                        self.result.successful += 1
                    else:
                        self.result.skipped += 1
                except Exception as e:
                    self.result.add_error(idx, None, str(e))

        except ImportError as e:
            self.result.add_error(0, None, str(e))

        return self.result

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
