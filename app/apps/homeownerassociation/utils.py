import os
import tempfile
import magic
from rest_framework import serializers


CSV_MIME_TYPES = ["text/csv", "text/plain", "application/csv"]


def validate_csv_file(value):
    """
    Validate that the uploaded file is a CSV file.
    Checks file extension and MIME type.
    """
    # Validate file extension
    if not value.name.lower().endswith(".csv"):
        raise serializers.ValidationError("File must be a CSV file")

    # Validate file is not empty
    if value.size == 0:
        raise serializers.ValidationError("File cannot be empty")

    # Validate MIME type
    try:
        mime = magic.Magic(mime=True)
        file_mime_type = mime.from_buffer(value.read(2048))
        value.seek(0)  # Reset file pointer

        if file_mime_type not in CSV_MIME_TYPES:
            raise serializers.ValidationError(
                f"Invalid file type. Expected CSV file, got {file_mime_type}"
            )
    except (ImportError, AttributeError):
        # If python-magic is not available or fails to initialize,
        # fall back to extension-only validation
        pass
    except Exception:
        # If MIME type detection fails for other reasons, still allow the file
        # if extension is correct (CSV files don't have reliable magic bytes)
        value.seek(0)  # Ensure file pointer is reset

    return value


def process_csv_import(file, importer):
    """
    Process a CSV import by saving the uploaded file to a temporary file,
    running the importer, and returning the serialized result.

    Args:
        file: The uploaded file object from the request
        importer: An instance of a BaseImporter subclass

    Returns:
        Dict containing the serialized import result

    Raises:
        Exception: If the import fails, the exception is raised
    """
    temp_file = None
    temp_file_path = None
    try:
        # Create temporary file
        fd, temp_file_path = tempfile.mkstemp(suffix=".csv", text=True)
        temp_file = os.fdopen(fd, "wb")

        # Write uploaded file content to temporary file
        for chunk in file.chunks():
            temp_file.write(chunk)
        temp_file.close()
        temp_file = None

        # Run import
        result = importer.import_file(temp_file_path)

        # Serialize result
        result_data = {
            "counts": {
                "total": result.total_rows,
                "successful": result.successful,
                "failed": result.failed,
                "skipped": result.skipped,
            },
            "errors": [
                {
                    "row_number": error.row_number,
                    "field": error.field,
                    "message": error.message,
                }
                for error in result.errors
            ],
            "warnings": result.warnings,
            "messages": result.messages,
        }

        return result_data

    finally:
        # Clean up temporary file
        if temp_file:
            try:
                temp_file.close()
            except Exception:
                pass
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
