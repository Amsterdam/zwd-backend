import tempfile
import os
from django.test import TestCase
from unittest.mock import patch
from model_bakery import baker

from apps.cases.models import Case
from apps.homeownerassociation.models import Contact, HomeownerAssociation
from apps.homeownerassociation.importers.contact_importer import ContactImporter


class ContactImporterTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.hoa = baker.make(
            HomeownerAssociation,
            name="Vereniging van Eigenaars Test",
            build_year=2010,
            number_of_apartments=10,
        )

    def _create_csv_file(self, content: str) -> str:
        """Helper to create a temporary CSV file"""
        fd, path = tempfile.mkstemp(suffix=".csv", text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _get_valid_csv_content(self) -> str:
        """Helper to get valid CSV content"""
        return """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
123EAK,V12345,Vereniging van Eigenaars Test,John Doe,john@example.com,Nee"""

    def test_import_creates_new_contact(self):
        """Test that importing a valid row creates a new contact"""
        csv_content = self._get_valid_csv_content()
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 1)
            self.assertEqual(result.failed, 0)
            self.assertEqual(result.total_rows, 1)

            # Verify contact was created
            contact = Contact.objects.filter(email="john@example.com").first()
            self.assertIsNotNone(contact)
            self.assertEqual(contact.fullname, "John Doe")
            self.assertEqual(contact.homeowner_association, self.hoa)
            self.assertEqual(contact.role, "Geïmporteerd contact")
            self.assertFalse(contact.is_primary)
        finally:
            os.unlink(csv_file)

    def test_import_updates_existing_contact(self):
        """Test that importing updates an existing contact"""
        # Create existing contact
        existing_contact = baker.make(
            Contact,
            email="john@example.com",
            homeowner_association=self.hoa,
            fullname="Old Name",
            phone="123456789",
            role="Old Role",
        )

        csv_content = self._get_valid_csv_content()
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 1)
            self.assertEqual(result.failed, 0)

            # Verify contact was updated
            existing_contact.refresh_from_db()
            self.assertEqual(existing_contact.fullname, "John Doe")
            self.assertEqual(existing_contact.phone, "123456789")  # Preserved
            self.assertEqual(existing_contact.role, "Old Role")  # Preserved
        finally:
            os.unlink(csv_file)

    def test_import_finds_hoa_by_prefixed_dossier_id(self):
        """Test finding HOA by Case prefixed_dossier_id (ZWD)"""
        case = baker.make(
            Case,
            prefixed_dossier_id="123EAK",
            homeowner_association=self.hoa,
        )

        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
123EAK,,,John Doe,john@example.com,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 1)
            self.assertEqual(result.failed, 0)

            contact = Contact.objects.filter(email="john@example.com").first()
            self.assertIsNotNone(contact)
            self.assertEqual(contact.homeowner_association, self.hoa)
        finally:
            os.unlink(csv_file)

    def test_import_finds_hoa_by_legacy_id(self):
        """Test finding HOA by Case legacy_id (Vnummer)"""
        case = baker.make(
            Case,
            legacy_id="V12345",
            homeowner_association=self.hoa,
        )

        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,V12345,,John Doe,john@example.com,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 1)
            self.assertEqual(result.failed, 0)

            contact = Contact.objects.filter(email="john@example.com").first()
            self.assertIsNotNone(contact)
            self.assertEqual(contact.homeowner_association, self.hoa)
        finally:
            os.unlink(csv_file)

    def test_import_finds_hoa_by_name(self):
        """Test finding HOA by exact name match"""
        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,,Vereniging van Eigenaars Test,John Doe,john@example.com,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 1)
            self.assertEqual(result.failed, 0)

            contact = Contact.objects.filter(email="john@example.com").first()
            self.assertIsNotNone(contact)
            self.assertEqual(contact.homeowner_association, self.hoa)
        finally:
            os.unlink(csv_file)

    @patch("apps.homeownerassociation.models.DsoClient")
    @patch("apps.homeownerassociation.models.KvkClient")
    def test_import_creates_hoa_from_api_when_not_found(
        self, MockKvkClient, MockDsoClient
    ):
        """Test that importer creates HOA from API when not found in database"""
        # Mock external API calls
        mock_dso_client = MockDsoClient.return_value
        mock_dso_client.get_hoa_by_name.return_value = [
            {
                "pndOorspronkelijkBouwjaar": 2015,
                "postcode": "1012AB",
                "gbdSdlNaam": "Centrum",
                "gbdBrtNaam": "Binnenstad",
                "gbdWijkNaam": "Wijk1",
                "mntMonumentstatus": "Rijksmonument",
                "bsdLigtInBeschermdGebied": "Ja",
                "bsdBeschermdStadsdorpsgezicht": "Nee",
            }
        ]

        mock_kvk_client = MockKvkClient.return_value
        mock_kvk_client.search_kvk_by_hoa_name.return_value = "12345678"

        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,,New HOA Name,John Doe,john@example.com,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=False)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 1)
            self.assertEqual(result.failed, 0)

            # Verify HOA was created
            new_hoa = HomeownerAssociation.objects.filter(name="New HOA Name").first()
            self.assertIsNotNone(new_hoa)
            self.assertEqual(new_hoa.build_year, 2015)
            self.assertEqual(new_hoa.zip_code, "1012AB")

            # Verify contact was created
            contact = Contact.objects.filter(email="john@example.com").first()
            self.assertIsNotNone(contact)
            self.assertEqual(contact.homeowner_association, new_hoa)
        finally:
            os.unlink(csv_file)

    def test_import_fails_when_hoa_not_found(self):
        """Test that import fails when HOA cannot be found"""
        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,,Non-existent HOA,John Doe,john@example.com,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 0)
            self.assertEqual(result.failed, 1)
            self.assertGreater(len(result.errors), 0)
            self.assertIn("Could not find homeowner association", str(result.errors[0]))
        finally:
            os.unlink(csv_file)

    def test_import_validates_email_format(self):
        """Test that invalid email addresses are rejected"""
        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,,Vereniging van Eigenaars Test,John Doe,invalid-email,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 0)
            self.assertEqual(result.failed, 1)
            self.assertGreater(len(result.errors), 0)
            self.assertIn("Invalid email format", str(result.errors[0]))
        finally:
            os.unlink(csv_file)

    def test_import_requires_email(self):
        """Test that missing email is rejected"""
        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,,Vereniging van Eigenaars Test,John Doe,,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 0)
            self.assertEqual(result.failed, 1)
            self.assertGreater(len(result.errors), 0)
            self.assertIn("Email address is required", str(result.errors[0]))
        finally:
            os.unlink(csv_file)

    def test_dry_run_mode_does_not_create_contacts(self):
        """Test that dry-run mode validates but doesn't save data"""
        csv_content = self._get_valid_csv_content()
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=True, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 1)
            self.assertEqual(result.failed, 0)

            # Verify no contact was created
            contact_count = Contact.objects.filter(email="john@example.com").count()
            self.assertEqual(contact_count, 0)

            # Verify dry-run message was added
            self.assertGreater(len(result.messages), 0)
            self.assertIn("DRY RUN", result.messages[0])
        finally:
            os.unlink(csv_file)

    @patch("apps.homeownerassociation.models.DsoClient")
    @patch("apps.homeownerassociation.models.KvkClient")
    def test_dry_run_mode_checks_api_but_doesnt_create_hoa(
        self, MockKvkClient, MockDsoClient
    ):
        """Test that dry-run mode checks API but doesn't create HOA"""
        mock_dso_client = MockDsoClient.return_value
        mock_dso_client.get_hoa_by_name.return_value = [
            {
                "pndOorspronkelijkBouwjaar": 2015,
                "postcode": "1012AB",
                "gbdSdlNaam": "Centrum",
                "gbdBrtNaam": "Binnenstad",
                "gbdWijkNaam": "Wijk1",
            }
        ]

        mock_kvk_client = MockKvkClient.return_value
        mock_kvk_client.search_kvk_by_hoa_name.return_value = "12345678"

        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,,New HOA Name,John Doe,john@example.com,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=True, skip_hoa_api=False)
            result = importer.import_file(csv_file)

            # Should fail because HOA doesn't exist and dry-run doesn't create it
            self.assertEqual(result.successful, 0)
            self.assertEqual(result.failed, 1)

            # Verify HOA was not created
            hoa_count = HomeownerAssociation.objects.filter(name="New HOA Name").count()
            self.assertEqual(hoa_count, 0)

            # Verify API was called (dry-run checks but doesn't create)
            mock_dso_client.get_hoa_by_name.assert_called()
        finally:
            os.unlink(csv_file)

    def test_import_validates_required_columns(self):
        """Test that missing required columns raise an error"""
        csv_content = """ZWD,Vnummer,Kontaktpersoon,Mailadres
123EAK,V12345,John Doe,john@example.com"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 0)
            self.assertEqual(result.failed, 1)
            self.assertGreater(len(result.errors), 0)
            self.assertIn("Missing required columns", str(result.errors[0]))
        finally:
            os.unlink(csv_file)

    def test_import_handles_case_without_hoa(self):
        """Test warning when case exists but has no homeowner_association"""
        case = baker.make(
            Case, prefixed_dossier_id="123EAK", homeowner_association=None
        )

        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
123EAK,,,John Doe,john@example.com,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 0)
            self.assertEqual(result.failed, 1)
            self.assertGreater(len(result.warnings), 0)
            self.assertIn("has no homeowner_association", result.warnings[0])
        finally:
            os.unlink(csv_file)

    def test_import_handles_empty_gestopt_field(self):
        """Test that empty Gestopt field defaults to active"""
        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,,Vereniging van Eigenaars Test,John Doe,john@example.com,"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 1)

            contact = Contact.objects.filter(email="john@example.com").first()
            self.assertIsNotNone(contact)
        finally:
            os.unlink(csv_file)

    def test_import_handles_case_insensitive_email_matching(self):
        """Test that contact lookup is case-insensitive for email"""
        existing_contact = baker.make(
            Contact,
            email="John@Example.com",
            homeowner_association=self.hoa,
            fullname="Old Name",
        )

        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,,Vereniging van Eigenaars Test,John Doe,john@example.com,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 1)

            # Should update existing contact (case-insensitive match)
            existing_contact.refresh_from_db()
            self.assertEqual(existing_contact.fullname, "John Doe")
        finally:
            os.unlink(csv_file)

    def test_import_handles_multiple_rows(self):
        """Test importing multiple rows"""
        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,,Vereniging van Eigenaars Test,John Doe,john@example.com,Nee
,,Vereniging van Eigenaars Test,Jane Smith,jane@example.com,Ja"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 2)
            self.assertEqual(result.failed, 0)
            self.assertEqual(result.total_rows, 2)

            # Verify both contacts were created
            john = Contact.objects.filter(email="john@example.com").first()
            jane = Contact.objects.filter(email="jane@example.com").first()
            self.assertIsNotNone(john)
            self.assertIsNotNone(jane)
        finally:
            os.unlink(csv_file)

    def test_import_handles_mixed_success_and_failure(self):
        """Test that some rows can succeed while others fail"""
        csv_content = """ZWD,Vnummer,Statutaire Naam,Kontaktpersoon,Mailadres,Gestopt
,,Vereniging van Eigenaars Test,John Doe,john@example.com,Nee
,,Non-existent HOA,Jane Smith,jane@example.com,Nee
,,Vereniging van Eigenaars Test,Invalid Email,invalid-email,Nee"""
        csv_file = self._create_csv_file(csv_content)

        try:
            importer = ContactImporter(dry_run=False, skip_hoa_api=True)
            result = importer.import_file(csv_file)

            self.assertEqual(result.successful, 1)
            self.assertEqual(result.failed, 2)
            self.assertEqual(result.total_rows, 3)

            # Verify only valid contact was created
            john = Contact.objects.filter(email="john@example.com").first()
            self.assertIsNotNone(john)
            self.assertEqual(Contact.objects.count(), 1)
        finally:
            os.unlink(csv_file)
