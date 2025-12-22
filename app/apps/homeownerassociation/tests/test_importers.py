import tempfile
import os
from datetime import datetime
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from model_bakery import baker

from apps.homeownerassociation.models import (
    HomeownerAssociation,
    Contact,
    HomeownerAssociationCommunicationNote,
)
from apps.cases.models import Case
from apps.homeownerassociation.importers.base import (
    BaseImporter,
    ImportError,
    ImportResult,
    RowError,
)
from apps.homeownerassociation.importers.letter_importer import LetterImporter
from apps.homeownerassociation.importers.course_participant_importer import (
    CourseParticipantImporter,
)
from apps.homeownerassociation.importers.contact_importer import ContactImporter


class TestImporterBase(TestCase):
    """Base class for importer tests with helper methods"""

    def create_temp_csv(self, content: str) -> str:
        """Create a temporary CSV file with given content"""
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def tearDown(self):
        """Clean up any temporary files"""


class RowErrorTest(TestCase):
    """Test RowError class"""

    def test_row_error_with_field(self):
        error = RowError(5, "email", "Ongeldig e-mailadres")
        self.assertEqual(str(error), "Rij 5, veld 'email': Ongeldig e-mailadres")

    def test_row_error_without_field(self):
        error = RowError(10, None, "Algemene fout")
        self.assertEqual(str(error), "Rij 10: Algemene fout")


class ImportResultTest(TestCase):
    """Test ImportResult class"""

    def test_import_result_initialization(self):
        result = ImportResult()
        self.assertEqual(result.total_rows, 0)
        self.assertEqual(result.successful, 0)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)
        self.assertEqual(len(result.messages), 0)

    def test_add_error(self):
        result = ImportResult()
        result.add_error(2, "email", "Ongeldig formaat")
        self.assertEqual(result.failed, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertIn(2, result.failed_rows)

    def test_add_error_same_row_twice(self):
        result = ImportResult()
        result.add_error(2, "email", "Eerste fout")
        result.add_error(2, "naam", "Tweede fout")
        self.assertEqual(result.failed, 1)  # Only counted once
        self.assertEqual(len(result.errors), 2)  # But both errors recorded

    def test_add_warning(self):
        result = ImportResult()
        result.add_warning("Er ging wat fout")
        self.assertEqual(len(result.warnings), 1)

    def test_add_message(self):
        result = ImportResult()
        result.add_message("Informatie over import")
        self.assertEqual(len(result.messages), 1)

    def test_str_representation(self):
        result = ImportResult()
        result.total_rows = 10
        result.successful = 7
        result.failed = 2
        result.skipped = 1
        expected = "Import voltooid: 7 succesvol, 2 mislukt, 1 overgeslagen van 10 totaal aantal rijen"
        self.assertEqual(str(result), expected)


class BaseImporterTest(TestImporterBase):
    """Test BaseImporter functionality"""

    class TestImporter(BaseImporter):
        """Concrete implementation for testing"""

        def _process_row(self, row, row_number):
            email = row.get("email", "").strip()
            if not email:
                self._add_error(row_number, "email", "E-mail is verplicht")
                return False
            if not self._validate_email(email):
                self._add_error(row_number, "email", "Ongeldig e-mailadres")
                return False
            return True

    def test_detect_encoding_utf8(self):
        content = "naam,email\nJan,jan@test.nl"
        csv_path = self.create_temp_csv(content)
        importer = self.TestImporter(required_columns=["naam", "email"])
        encoding = importer._detect_encoding(csv_path)
        self.assertIn(encoding, ["utf-8", "utf-8-sig"])

    def test_detect_delimiter_semicolon(self):
        importer = self.TestImporter(required_columns=[])
        delimiter = importer._detect_delimiter("naam;email;telefoon")
        self.assertEqual(delimiter, ";")

    def test_detect_delimiter_comma(self):
        importer = self.TestImporter(required_columns=[])
        delimiter = importer._detect_delimiter("naam,email,telefoon")
        self.assertEqual(delimiter, ",")

    def test_detect_delimiter_single_column(self):
        importer = self.TestImporter(required_columns=[])
        delimiter = importer._detect_delimiter("vve")
        self.assertIsNone(delimiter)

    def test_read_csv_with_semicolon(self):
        content = "naam;email\nJan;jan@test.nl\nPiet;piet@test.nl"
        csv_path = self.create_temp_csv(content)
        importer = self.TestImporter(required_columns=["naam", "email"])
        headers, rows = importer._read_csv(csv_path)
        self.assertEqual(headers, ["naam", "email"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["naam"], "Jan")
        self.assertEqual(rows[0]["email"], "jan@test.nl")

    def test_read_csv_with_comma(self):
        content = "naam,email\nJan,jan@test.nl"
        csv_path = self.create_temp_csv(content)
        importer = self.TestImporter(required_columns=["naam", "email"])
        headers, rows = importer._read_csv(csv_path)
        self.assertEqual(headers, ["naam", "email"])
        self.assertEqual(len(rows), 1)

    def test_read_csv_single_column(self):
        content = "vve\nVereniging 1\nVereniging 2"
        csv_path = self.create_temp_csv(content)
        importer = self.TestImporter(required_columns=["vve"])
        headers, rows = importer._read_csv(csv_path)
        self.assertEqual(headers, ["vve"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["vve"], "Vereniging 1")

    def test_read_csv_with_bom(self):
        content = "\ufeffnaam,email\nJan,jan@test.nl"
        csv_path = self.create_temp_csv(content)
        importer = self.TestImporter(required_columns=["naam", "email"])
        headers, rows = importer._read_csv(csv_path)
        self.assertEqual(headers, ["naam", "email"])
        self.assertNotIn("\ufeff", headers[0])

    def test_read_csv_strips_whitespace(self):
        content = " naam , email \n  Jan  ,  jan@test.nl  "
        csv_path = self.create_temp_csv(content)
        importer = self.TestImporter(required_columns=["naam", "email"])
        headers, rows = importer._read_csv(csv_path)
        self.assertEqual(headers, ["naam", "email"])
        self.assertEqual(rows[0]["naam"], "Jan")
        self.assertEqual(rows[0]["email"], "jan@test.nl")

    def test_read_csv_empty_file(self):
        content = ""
        csv_path = self.create_temp_csv(content)
        importer = self.TestImporter(required_columns=[])
        with self.assertRaises(ImportError) as context:
            importer._read_csv(csv_path)
        self.assertIn("leeg", str(context.exception))

    def test_read_csv_file_not_found(self):
        importer = self.TestImporter(required_columns=[])
        with self.assertRaises(ImportError) as context:
            importer._read_csv("/nonexistent/file.csv")
        self.assertIn("niet gevonden", str(context.exception).lower())

    def test_validate_headers_success(self):
        importer = self.TestImporter(required_columns=["naam", "email"])
        importer._validate_headers(["naam", "email", "telefoon"])

    def test_validate_headers_missing_columns(self):
        importer = self.TestImporter(required_columns=["naam", "email", "telefoon"])
        with self.assertRaises(ImportError) as context:
            importer._validate_headers(["naam", "email"])
        self.assertIn("Ontbrekende verplichte kolommen", str(context.exception))
        self.assertIn("telefoon", str(context.exception))

    def test_validate_email_valid(self):
        importer = self.TestImporter(required_columns=[])
        self.assertTrue(importer._validate_email("test@example.com"))
        self.assertTrue(importer._validate_email("user.name+tag@example.co.uk"))

    def test_validate_email_invalid(self):
        importer = self.TestImporter(required_columns=[])
        self.assertFalse(importer._validate_email("invalid"))
        self.assertFalse(importer._validate_email("@example.com"))
        self.assertFalse(importer._validate_email("test@"))
        self.assertFalse(importer._validate_email(""))

    def test_import_file_success(self):
        content = "naam,email\nJan,jan@test.nl\nPiet,piet@test.nl"
        csv_path = self.create_temp_csv(content)
        importer = self.TestImporter(required_columns=["naam", "email"])
        result = importer.import_file(csv_path)
        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.successful, 2)
        self.assertEqual(result.failed, 0)

    def test_import_file_with_errors(self):
        content = "naam,email\nJan,jan@test.nl\nPiet,invalid-email\nKlaas,"
        csv_path = self.create_temp_csv(content)
        importer = self.TestImporter(required_columns=["naam", "email"])
        result = importer.import_file(csv_path)
        self.assertEqual(result.total_rows, 3)
        self.assertEqual(result.successful, 1)
        self.assertEqual(result.failed, 2)

    def test_find_homeowner_association_by_name_exists(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        importer = self.TestImporter(required_columns=[])
        result = importer._find_homeowner_association_by_name("Test Vve", 1)
        self.assertEqual(result.name, "Test Vve")

    def test_find_homeowner_association_by_name_not_found(self):
        importer = self.TestImporter(required_columns=[])
        with patch.object(
            HomeownerAssociation, "_get_hoa_data", side_effect=ValueError("No data")
        ):
            result = importer._find_homeowner_association_by_name(
                "Nonexistent Vve", 1, skip_hoa_api=True
            )
            self.assertIsNone(result)

    def test_find_homeowner_association_by_name_empty_name(self):
        importer = self.TestImporter(required_columns=[])
        result = importer._find_homeowner_association_by_name("", 1)
        self.assertIsNone(result)


class LetterImporterTest(TestImporterBase):
    """Test LetterImporter functionality"""

    def setUp(self):
        self.date = timezone.make_aware(datetime(2025, 1, 15, 10, 0))
        self.description = "Brief verzonden over onderhoudsadvies"
        self.author_name = "Test Adviseur"

    def test_process_row_success(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        importer = LetterImporter(
            date=self.date,
            description=self.description,
            author_name=self.author_name,
            skip_hoa_api=True,
        )
        importer._existing_hoa_cache = {"Test Vve": hoa}

        row = {"vve": "Test Vve"}
        result = importer._process_row(row, 2)

        self.assertTrue(result)
        self.assertIn("Test Vve", importer._processed_hoa_names)
        self.assertEqual(len(importer._notes_to_create), 1)
        note = importer._notes_to_create[0]
        self.assertEqual(note.homeowner_association, hoa)
        self.assertEqual(note.note, self.description)
        self.assertEqual(note.author_name, self.author_name)
        self.assertTrue(note.is_imported)

    def test_process_row_duplicate_hoa(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        importer = LetterImporter(
            date=self.date,
            description=self.description,
            author_name=self.author_name,
            skip_hoa_api=True,
        )
        importer._existing_hoa_cache = {"Test Vve": hoa}
        importer._processed_hoa_names.add("Test Vve")

        row = {"vve": "Test Vve"}
        result = importer._process_row(row, 3)

        self.assertFalse(result)
        self.assertEqual(len(importer._notes_to_create), 0)
        self.assertTrue(any("Dubbele vve" in msg for msg in importer.result.messages))

    def test_process_row_hoa_not_found(self):
        importer = LetterImporter(
            date=self.date,
            description=self.description,
            author_name=self.author_name,
            skip_hoa_api=True,
        )
        importer._existing_hoa_cache = {}

        row = {"vve": "Nonexistent Vve"}
        result = importer._process_row(row, 2)

        self.assertFalse(result)
        self.assertEqual(len(importer.result.errors), 1)
        self.assertIn("Kon vve niet vinden", str(importer.result.errors[0]))

    def test_process_row_dry_run(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        importer = LetterImporter(
            date=self.date,
            description=self.description,
            author_name=self.author_name,
            dry_run=True,
            skip_hoa_api=True,
        )
        importer._existing_hoa_cache = {"Test Vve": hoa}

        row = {"vve": "Test Vve"}
        result = importer._process_row(row, 2)

        self.assertTrue(result)
        self.assertEqual(len(importer._notes_to_create), 0)  # No actual notes created
        self.assertTrue(any("DRY RUN" in msg for msg in importer.result.messages))

    def test_import_file_with_valid_data(self):
        baker.make(HomeownerAssociation, name="Vve A")
        baker.make(HomeownerAssociation, name="Vve B")

        content = "vve\nVve A\nVve B"
        csv_path = self.create_temp_csv(content)

        importer = LetterImporter(
            date=self.date,
            description=self.description,
            author_name=self.author_name,
            skip_hoa_api=True,
        )
        result = importer.import_file(csv_path)

        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.successful, 2)
        self.assertEqual(result.failed, 0)

        # Check that notes were created
        notes = HomeownerAssociationCommunicationNote.objects.filter(is_imported=True)
        self.assertEqual(notes.count(), 2)

    def test_import_file_skips_existing_notes(self):
        hoa = baker.make(HomeownerAssociation, name="Vve A")
        # Create an existing note for the same date
        baker.make(
            HomeownerAssociationCommunicationNote,
            homeowner_association=hoa,
            date=self.date,
            is_imported=True,
        )

        content = "vve\nVve A"
        csv_path = self.create_temp_csv(content)

        importer = LetterImporter(
            date=self.date,
            description=self.description,
            author_name=self.author_name,
            skip_hoa_api=True,
        )
        result = importer.import_file(csv_path)

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.successful, 0)
        self.assertEqual(result.skipped, 1)
        self.assertTrue(
            any("Dubbele import" in msg for msg in importer.result.messages)
        )


class CourseParticipantImporterTest(TestImporterBase):
    """Test CourseParticipantImporter functionality"""

    def test_process_row_success_new_contact(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        importer = CourseParticipantImporter(skip_hoa_api=True)

        with patch.object(importer, "_find_homeowner_association", return_value=hoa):
            row = {
                "naam": "Jan Janssen",
                "email": "jan@test.nl",
                "telefoon": "0612345678",
                "functie": "Bestuurslid",
                "cursusdatum": "15/11/2025",
                "vve": "Test Vve",
            }
            result = importer._process_row(row, 2)

        self.assertTrue(result)
        contact = Contact.objects.get(email="jan@test.nl")
        self.assertEqual(contact.fullname, "Jan Janssen")
        self.assertEqual(contact.phone, "0612345678")
        self.assertEqual(contact.role, "Bestuurslid")
        self.assertEqual(contact.course_date.strftime("%d/%m/%Y"), "15/11/2025")

    def test_process_row_update_existing_contact(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        baker.make(
            Contact,
            email="jan@test.nl",
            homeowner_association=hoa,
            fullname="Jan",
            role="Lid",
        )

        importer = CourseParticipantImporter(skip_hoa_api=True)

        with patch.object(importer, "_find_homeowner_association", return_value=hoa):
            row = {
                "naam": "Jan Janssen (Updated)",
                "email": "jan@test.nl",
                "telefoon": "0687654321",
                "functie": "Voorzitter",
                "cursusdatum": "20/11/2025",
                "vve": "Test Vve",
            }
            result = importer._process_row(row, 2)

        self.assertTrue(result)
        contact = Contact.objects.get(email="jan@test.nl")
        self.assertEqual(contact.fullname, "Jan Janssen (Updated)")
        self.assertEqual(contact.role, "Voorzitter")

    def test_process_row_missing_email(self):
        importer = CourseParticipantImporter(skip_hoa_api=True)
        row = {
            "naam": "Jan Janssen",
            "email": "",
            "cursusdatum": "15/11/2025",
            "vve": "Test Vve",
        }
        result = importer._process_row(row, 2)

        self.assertFalse(result)
        self.assertEqual(len(importer.result.errors), 1)
        self.assertIn("verplicht", str(importer.result.errors[0]))

    def test_process_row_invalid_email(self):
        importer = CourseParticipantImporter(skip_hoa_api=True)
        row = {
            "naam": "Jan Janssen",
            "email": "invalid-email",
            "cursusdatum": "15/11/2025",
            "vve": "Test Vve",
        }
        result = importer._process_row(row, 2)

        self.assertFalse(result)
        self.assertEqual(len(importer.result.errors), 1)
        self.assertIn("Ongeldig e-mailadres", str(importer.result.errors[0]))

    def test_parse_course_date_valid(self):
        importer = CourseParticipantImporter(skip_hoa_api=True)
        date = importer._parse_course_date("25/11/2025 00:00", 1)
        self.assertIsNotNone(date)
        self.assertEqual(date.day, 25)
        self.assertEqual(date.month, 11)
        self.assertEqual(date.year, 2025)

    def test_parse_course_date_without_time(self):
        importer = CourseParticipantImporter(skip_hoa_api=True)
        date = importer._parse_course_date("25/11/2025", 1)
        self.assertIsNotNone(date)
        self.assertEqual(date.day, 25)

    def test_parse_course_date_invalid(self):
        importer = CourseParticipantImporter(skip_hoa_api=True)
        date = importer._parse_course_date("invalid-date", 1)
        self.assertIsNone(date)

    def test_process_row_missing_course_date(self):
        importer = CourseParticipantImporter(skip_hoa_api=True)
        row = {
            "naam": "Jan Janssen",
            "email": "jan@test.nl",
            "cursusdatum": "",
            "vve": "Test Vve",
        }
        result = importer._process_row(row, 2)

        self.assertFalse(result)
        self.assertIn("Cursusdatum is verplicht", str(importer.result.errors[0]))

    def test_process_row_hoa_not_found(self):
        importer = CourseParticipantImporter(skip_hoa_api=True)
        with patch.object(importer, "_find_homeowner_association", return_value=None):
            row = {
                "naam": "Jan Janssen",
                "email": "jan@test.nl",
                "cursusdatum": "15/11/2025",
                "vve": "Nonexistent Vve",
            }
            result = importer._process_row(row, 2)

        self.assertFalse(result)
        self.assertIn("Kon vve niet vinden", str(importer.result.errors[0]))

    def test_process_row_dry_run(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        importer = CourseParticipantImporter(dry_run=True, skip_hoa_api=True)

        with patch.object(importer, "_find_homeowner_association", return_value=hoa):
            row = {
                "naam": "Jan Janssen",
                "email": "jan@test.nl",
                "cursusdatum": "15/11/2025",
                "vve": "Test Vve",
            }
            result = importer._process_row(row, 2)

        self.assertTrue(result)
        self.assertFalse(Contact.objects.filter(email="jan@test.nl").exists())
        self.assertTrue(any("DRY RUN" in msg for msg in importer.result.messages))


class ContactImporterTest(TestImporterBase):
    """Test ContactImporter functionality"""

    def test_process_row_success_new_contact(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        importer = ContactImporter(skip_hoa_api=True)

        with patch.object(importer, "_find_homeowner_association", return_value=hoa):
            row = {
                "ZWD": "123EAK",
                "Vnummer": "V12345",
                "Statutaire Naam": "Test Vve",
                "Kontaktpersoon": "Jan Janssen",
                "Mailadres": "jan@test.nl",
            }
            result = importer._process_row(row, 2)

        self.assertTrue(result)
        contact = Contact.objects.get(email="jan@test.nl")
        self.assertEqual(contact.fullname, "Jan Janssen")
        self.assertEqual(contact.role, "Geïmporteerd contact")

    def test_process_row_update_existing_contact(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        existing_contact = baker.make(
            Contact, email="jan@test.nl", homeowner_association=hoa, fullname="Jan"
        )

        importer = ContactImporter(skip_hoa_api=True)

        with patch.object(importer, "_find_homeowner_association", return_value=hoa):
            row = {
                "ZWD": "123EAK",
                "Vnummer": "V12345",
                "Statutaire Naam": "Test Vve",
                "Kontaktpersoon": "Jan Janssen (Updated)",
                "Mailadres": "jan@test.nl",
            }
            result = importer._process_row(row, 2)

        self.assertTrue(result)
        contact = Contact.objects.get(email="jan@test.nl")
        self.assertEqual(contact.fullname, "Jan Janssen (Updated)")

    def test_find_homeowner_association_by_prefixed_dossier_id(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        baker.make(Case, prefixed_dossier_id="123EAK", homeowner_association=hoa)

        importer = ContactImporter(skip_hoa_api=True)
        row = {
            "ZWD": "123EAK",
            "Vnummer": "",
            "Statutaire Naam": "",
            "Mailadres": "test@test.nl",
        }
        result = importer._find_homeowner_association(row, 2)

        self.assertEqual(result, hoa)

    def test_find_homeowner_association_by_legacy_id(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        baker.make(Case, legacy_id="V12345", homeowner_association=hoa)

        importer = ContactImporter(skip_hoa_api=True)
        row = {
            "ZWD": "",
            "Vnummer": "V12345",
            "Statutaire Naam": "",
            "Mailadres": "test@test.nl",
        }
        result = importer._find_homeowner_association(row, 2)

        self.assertEqual(result, hoa)

    def test_find_homeowner_association_by_name(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")

        importer = ContactImporter(skip_hoa_api=True)
        row = {
            "ZWD": "",
            "Vnummer": "",
            "Statutaire Naam": "Test Vve",
            "Mailadres": "test@test.nl",
        }
        result = importer._find_homeowner_association(row, 2)

        self.assertEqual(result, hoa)

    def test_process_row_missing_email(self):
        importer = ContactImporter(skip_hoa_api=True)
        row = {
            "ZWD": "123EAK",
            "Vnummer": "V12345",
            "Statutaire Naam": "Test Vve",
            "Kontaktpersoon": "Jan Janssen",
            "Mailadres": "",
        }
        result = importer._process_row(row, 2)

        self.assertFalse(result)
        self.assertIn("verplicht", str(importer.result.errors[0]))

    def test_process_row_invalid_email(self):
        importer = ContactImporter(skip_hoa_api=True)
        row = {
            "ZWD": "123EAK",
            "Vnummer": "V12345",
            "Statutaire Naam": "Test Vve",
            "Kontaktpersoon": "Jan Janssen",
            "Mailadres": "invalid-email",
        }
        result = importer._process_row(row, 2)

        self.assertFalse(result)
        self.assertIn("Ongeldig e-mailadres", str(importer.result.errors[0]))

    def test_process_row_hoa_not_found(self):
        importer = ContactImporter(skip_hoa_api=True)
        row = {
            "ZWD": "999XXX",
            "Vnummer": "V99999",
            "Statutaire Naam": "Nonexistent Vve",
            "Kontaktpersoon": "Jan Janssen",
            "Mailadres": "jan@test.nl",
        }
        result = importer._process_row(row, 2)

        self.assertFalse(result)
        self.assertIn("Kon vve niet vinden", str(importer.result.errors[0]))

    def test_process_row_dry_run(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        importer = ContactImporter(dry_run=True, skip_hoa_api=True)

        with patch.object(importer, "_find_homeowner_association", return_value=hoa):
            row = {
                "ZWD": "123EAK",
                "Vnummer": "V12345",
                "Statutaire Naam": "Test Vve",
                "Kontaktpersoon": "Jan Janssen",
                "Mailadres": "jan@test.nl",
            }
            result = importer._process_row(row, 2)

        self.assertTrue(result)
        self.assertFalse(Contact.objects.filter(email="jan@test.nl").exists())
        self.assertTrue(any("DRY RUN" in msg for msg in importer.result.messages))

    def test_import_file_with_valid_data(self):
        hoa = baker.make(HomeownerAssociation, name="Test Vve")
        baker.make(Case, prefixed_dossier_id="123EAK", homeowner_association=hoa)

        content = "ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres\n123EAK,V12345,Test Vve,Jan Janssen,jan@test.nl"
        csv_path = self.create_temp_csv(content)

        importer = ContactImporter(skip_hoa_api=True)
        result = importer.import_file(csv_path)

        self.assertEqual(result.total_rows, 1)
        self.assertEqual(result.successful, 1)
        self.assertEqual(result.failed, 0)

        # Check contact was created
        contact = Contact.objects.get(email="jan@test.nl")
        self.assertEqual(contact.fullname, "Jan Janssen")
