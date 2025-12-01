from django.urls import reverse
from rest_framework.test import APITestCase
from django.core import management
from model_bakery import baker
from unittest.mock import patch, MagicMock
from apps.cases.models import Case
from utils.test_utils import get_authenticated_client
from apps.homeownerassociation.models import (
    Contact,
    District,
    HomeownerAssociation,
    HomeownerAssociationCommunicationNote,
    Wijk,
)


class HomeownerAssociationTest(APITestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()
        self.client = get_authenticated_client()

    def test_retrieve_cases_for_homeowner_associations(self):
        homeowner_association = baker.make(
            "homeownerassociation.HomeownerAssociation", name="Test HOA"
        )
        case = baker.make(Case, homeowner_association=homeowner_association)
        url = reverse("homeownerassociation-cases", args=[homeowner_association.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data[0]["homeowner_association"]["name"],
            homeowner_association.name,
        )
        self.assertEqual(
            response.data[0]["id"],
            case.id,
        )

    def test_retrieve_districts(self):
        url = reverse("district-list")

        district_included = baker.make(District, name="Included District")
        hoa_with_case = baker.make(
            HomeownerAssociation,
            district=district_included,
        )
        baker.make(Case, homeowner_association=hoa_with_case)
        baker.make(District, name="Excluded District")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(district_included.name, response.data)
        self.assertNotIn("Excluded District", response.data)

    def test_retrieve_wijken(self):
        url = reverse("wijk-list")
        wijk_included = baker.make(Wijk, name="Included Wijk")
        hoa_with_case = baker.make(
            HomeownerAssociation,
            wijk=wijk_included,
        )
        baker.make(Case, homeowner_association=hoa_with_case)
        baker.make(Wijk, name="Excluded Wijk")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(wijk_included.name, response.data)
        self.assertNotIn("Excluded Wijk", response.data)

    def test_get_hoa_contacts(self):
        hoa = baker.make(HomeownerAssociation)
        contact1 = baker.make(Contact, homeowner_association=hoa)
        contact2 = baker.make(Contact, homeowner_association=hoa)
        url = reverse("homeownerassociation-contacts", args=[hoa.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        returned_ids = {contact["id"] for contact in response.data}
        expected_ids = {contact1.id, contact2.id}
        self.assertSetEqual(returned_ids, expected_ids)

    def test_put_hoa_contacts(self):
        hoa = baker.make("homeownerassociation.HomeownerAssociation")
        contact_data = [
            {
                "fullname": "John Doe",
                "email": "john@example.com",
                "phone": "1234567890",
                "role": "President",
            },
            {
                "fullname": "Jane Smith",
                "email": "jane@example.com",
                "phone": "0987654321",
                "role": "Secretary",
            },
        ]
        url = reverse("homeownerassociation-contacts", args=[hoa.id])
        response = self.client.put(url, {"contacts": contact_data}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["detail"], "Contacts created or updated successfully"
        )

        # Verify contacts were created with correct data via GET
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(len(get_response.data), 2)
        contact_names = {contact["fullname"] for contact in get_response.data}
        self.assertSetEqual(contact_names, {"John Doe", "Jane Smith"})
        # Verify is_primary defaults to False and is included in response
        for contact in get_response.data:
            self.assertIn("is_primary", contact)
            self.assertFalse(contact["is_primary"])

    def test_put_hoa_contacts_with_empty_data(self):
        hoa = baker.make("homeownerassociation.HomeownerAssociation")
        url = reverse("homeownerassociation-contacts", args=[hoa.id])
        response = self.client.put(url, {"contacts": []}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "At least one contact is required")

    def test_put_hoa_contacts_update_existing(self):
        """Test that PUT can update existing contacts."""
        hoa = baker.make("homeownerassociation.HomeownerAssociation")
        existing_contact = baker.make(
            Contact,
            fullname="Old Name",
            email="old@example.com",
            homeowner_association=hoa,
        )

        contact_data = [
            {
                "id": existing_contact.id,
                "fullname": "New Name",
                "email": "new@example.com",
                "phone": "1234567890",
                "role": "President",
            }
        ]
        url = reverse("homeownerassociation-contacts", args=[hoa.id])
        response = self.client.put(url, {"contacts": contact_data}, format="json")
        self.assertEqual(response.status_code, 200)

        # Verify the contact was updated
        updated_contact = Contact.objects.get(id=existing_contact.id)
        self.assertEqual(updated_contact.fullname, "New Name")
        self.assertEqual(updated_contact.email, "new@example.com")
        self.assertFalse(updated_contact.is_primary)

    def test_put_hoa_contacts_nonexistent_id(self):
        """Test that PUT returns error for non-existent contact ID."""
        hoa = baker.make("homeownerassociation.HomeownerAssociation")

        contact_data = [
            {
                "id": 99999,
                "fullname": "John Doe",
                "email": "john@example.com",
                "phone": "1234567890",
                "role": "President",
                "is_primary": True,
            }
        ]
        url = reverse("homeownerassociation-contacts", args=[hoa.id])
        response = self.client.put(url, {"contacts": contact_data}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["detail"], "Contacts created or updated successfully"
        )

        # Verify a contact was created and associated with the HOA
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(len(get_response.data), 1)
        created = get_response.data[0]
        self.assertEqual(created["fullname"], "John Doe")
        self.assertEqual(created["email"], "john@example.com")
        self.assertEqual(created["phone"], "1234567890")
        self.assertEqual(created["role"], "President")
        self.assertTrue(created["is_primary"])

    def test_post_hoa_contacts_validation_required_fields(self):
        """Test that POST contacts validates required fields."""
        hoa = baker.make("homeownerassociation.HomeownerAssociation")

        # Test missing fullname
        contact_data = [
            {
                "email": "john@example.com",
                "phone": "1234567890",
                "role": "President",
            }
        ]
        url = reverse("homeownerassociation-contacts", args=[hoa.id])
        response = self.client.post(url, {"contacts": contact_data}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("fullname", str(response.data))

    def test_post_hoa_contacts_validation_email_format(self):
        """Test that POST contacts validates email format."""
        hoa = baker.make("homeownerassociation.HomeownerAssociation")

        contact_data = [
            {
                "fullname": "John Doe",
                "email": "invalid-email",
                "phone": "1234567890",
                "role": "President",
            }
        ]
        url = reverse("homeownerassociation-contacts", args=[hoa.id])
        response = self.client.post(url, {"contacts": contact_data}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", str(response.data))

    def test_post_hoa_contacts_validation_blank_fields(self):
        """Test that POST contacts validates against blank fields."""
        hoa = baker.make("homeownerassociation.HomeownerAssociation")

        contact_data = [
            {
                "fullname": "",
                "email": "john@example.com",
                "phone": "1234567890",
                "role": "President",
            }
        ]
        url = reverse("homeownerassociation-contacts", args=[hoa.id])
        response = self.client.post(url, {"contacts": contact_data}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("fullname", str(response.data))

    def test_delete_contact_deleted(self):
        """Test that deleting a contact removes it completely since each contact belongs to one HOA."""
        hoa = baker.make(HomeownerAssociation)
        contact = baker.make(Contact, homeowner_association=hoa)

        url = reverse("homeownerassociation-delete", args=[hoa.id, contact.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        with self.assertRaises(Contact.DoesNotExist):
            Contact.objects.get(id=contact.id)

    def test_delete_contact_exclusive_deleted(self):
        hoa = baker.make(HomeownerAssociation)
        contact = baker.make(Contact, homeowner_association=hoa)

        url = reverse("homeownerassociation-delete", args=[hoa.id, contact.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        with self.assertRaises(Contact.DoesNotExist):
            Contact.objects.get(id=contact.id)

    @patch("apps.homeownerassociation.views.DsoClient")
    def test_apartments_returns_mapped_fields(self, dso_client_cls):
        """Test that apartments endpoint correctly maps DSO client response fields."""
        hoa = baker.make(HomeownerAssociation, name="VvE Test")

        # Mock the DSO client instance
        dso_client = MagicMock()
        dso_client.get_hoa_by_name.return_value = [
            {
                "adres": "Keizersgracht",
                "huisnummer": 1,
                "huisletter": "A",
                "huisnummertoevoeging": "III",
                "postcode": "1015AB",
                "woonplaats": "Amsterdam",
                "votIdentificatie": "VOT-123",
                "bagNagId": "NAG-456",
                "eigCategorieEigenaar": "Onderneming",
                "brkStatutaireNaam": "Veel Geld BV",
            }
        ]
        dso_client_cls.return_value = dso_client

        url = reverse("homeownerassociation-apartments", args=[hoa.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        apartment_data = response.data[0]

        # Verify field mapping
        self.assertEqual(apartment_data["straatnaam"], "Keizersgracht")
        self.assertEqual(apartment_data["huisnummer"], 1)
        self.assertEqual(apartment_data["huisletter"], "A")
        self.assertEqual(apartment_data["huisnummertoevoeging"], "III")
        self.assertEqual(apartment_data["postcode"], "1015AB")
        self.assertEqual(apartment_data["woonplaats"], "Amsterdam")
        self.assertEqual(apartment_data["adresseerbaarobject_id"], "VOT-123")
        self.assertEqual(apartment_data["nummeraanduiding_id"], "NAG-456")
        self.assertEqual(apartment_data["eigenaar_type"], "Onderneming")
        self.assertEqual(apartment_data["eigenaar_naam"], "Veel Geld BV")

        # Verify DSO client was called with HOA name
        dso_client.get_hoa_by_name.assert_called_once_with(hoa.name)

    @patch("apps.homeownerassociation.views.DsoClient")
    def test_apartments_handles_empty_response(self, dso_client_cls):
        """Test that apartments endpoint handles empty DSO client response."""
        hoa = baker.make(HomeownerAssociation, name="VvE Empty")

        # Mock empty response
        dso_client = MagicMock()
        dso_client.get_hoa_by_name.return_value = []
        dso_client_cls.return_value = dso_client

        url = reverse("homeownerassociation-apartments", args=[hoa.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
        dso_client.get_hoa_by_name.assert_called_once_with(hoa.name)

    @patch("apps.homeownerassociation.views.DsoClient")
    def test_apartments_handles_missing_fields(self, dso_client_cls):
        """Test that apartments endpoint handles missing or null fields gracefully."""
        hoa = baker.make(HomeownerAssociation, name="VvE Incomplete")

        # Mock response with missing/null fields
        dso_client = MagicMock()
        dso_client.get_hoa_by_name.return_value = [
            {
                "adres": "Prinsengracht",
                "huisnummer": None,
                "postcode": "1016AB",
                "votIdentificatie": "VOT-789",
                # Missing huisletter, huisnummertoevoeging, woonplaats, bagNagId, eigCategorieEigenaar, brkStatutaireNaam
            }
        ]
        dso_client_cls.return_value = dso_client

        url = reverse("homeownerassociation-apartments", args=[hoa.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        apartment_data = response.data[0]

        # Verify present fields
        self.assertEqual(apartment_data["straatnaam"], "Prinsengracht")
        self.assertEqual(apartment_data["postcode"], "1016AB")
        self.assertEqual(apartment_data["adresseerbaarobject_id"], "VOT-789")

        # Verify missing fields are handled (None values)
        self.assertIsNone(apartment_data["huisnummer"])
        self.assertIsNone(apartment_data["huisletter"])
        self.assertIsNone(apartment_data["huisnummertoevoeging"])
        self.assertIsNone(apartment_data["woonplaats"])
        self.assertIsNone(apartment_data["nummeraanduiding_id"])
        self.assertIsNone(apartment_data["eigenaar_type"])
        self.assertIsNone(apartment_data["eigenaar_naam"])

    def test_apartments_requires_valid_hoa_id(self):
        """Test that apartments endpoint returns 404 for non-existent HOA."""
        url = reverse("homeownerassociation-apartments", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_patch_hoa_annotation_success(self):
        """Test that PATCH successfully updates only the annotation field."""
        hoa = baker.make(
            HomeownerAssociation,
            name="Test HOA",
            annotation="Original annotation",
            build_year=2010,
            number_of_apartments=10,
        )

        url = reverse("homeownerassociation-detail", args=[hoa.id])
        new_annotation = "Updated annotation via PATCH"
        response = self.client.patch(url, {"annotation": new_annotation}, format="json")

        self.assertEqual(response.status_code, 200)

        # Verify the annotation was updated
        hoa.refresh_from_db()
        self.assertEqual(hoa.annotation, new_annotation)

        # Verify other fields were not affected
        self.assertEqual(hoa.name, "Test HOA")
        self.assertEqual(hoa.build_year, 2010)
        self.assertEqual(hoa.number_of_apartments, 10)

    def test_patch_hoa_annotation_only_allows_annotation_field(self):
        """Test that PATCH only allows updating the annotation field and ignores other fields."""
        hoa = baker.make(
            HomeownerAssociation,
            name="Test HOA",
            annotation="Original annotation",
            build_year=2010,
            number_of_apartments=10,
        )

        url = reverse("homeownerassociation-detail", args=[hoa.id])
        response = self.client.patch(
            url,
            {
                "annotation": "Updated annotation",
                "name": "Should not update",
                "build_year": 2020,
                "number_of_apartments": 20,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        # Verify only annotation was updated
        hoa.refresh_from_db()
        self.assertEqual(hoa.annotation, "Updated annotation")
        self.assertEqual(hoa.name, "Test HOA")  # Should remain unchanged
        self.assertEqual(hoa.build_year, 2010)  # Should remain unchanged
        self.assertEqual(hoa.number_of_apartments, 10)  # Should remain unchanged

    def test_patch_hoa_annotation_with_empty_string(self):
        """Test that PATCH allows updating annotation to empty string."""
        hoa = baker.make(
            HomeownerAssociation,
            name="Test HOA",
            annotation="Original annotation",
        )

        url = reverse("homeownerassociation-detail", args=[hoa.id])
        response = self.client.patch(url, {"annotation": ""}, format="json")

        self.assertEqual(response.status_code, 200)

        # Verify the annotation was cleared
        hoa.refresh_from_db()
        self.assertEqual(hoa.annotation, "")

    def test_patch_hoa_annotation_with_null_value(self):
        """Test that PATCH allows updating annotation to null."""
        hoa = baker.make(
            HomeownerAssociation,
            name="Test HOA",
            annotation="Original annotation",
        )

        url = reverse("homeownerassociation-detail", args=[hoa.id])
        response = self.client.patch(url, {"annotation": None}, format="json")

        self.assertEqual(response.status_code, 200)

        # Verify the annotation was set to null
        hoa.refresh_from_db()
        self.assertIsNone(hoa.annotation)

    def test_patch_hoa_annotation_nonexistent_hoa(self):
        """Test that PATCH returns 404 for non-existent HOA."""
        url = reverse("homeownerassociation-detail", args=[9999])
        response = self.client.patch(
            url, {"annotation": "New annotation"}, format="json"
        )

        self.assertEqual(response.status_code, 404)

    def test_patch_hoa_annotation_without_annotation_field(self):
        """Test that PATCH with empty data still works (no fields to update)."""
        hoa = baker.make(
            HomeownerAssociation,
            name="Test HOA",
            annotation="Original annotation",
        )

        url = reverse("homeownerassociation-detail", args=[hoa.id])
        response = self.client.patch(url, {}, format="json")

        self.assertEqual(response.status_code, 200)

        # Verify no changes were made
        hoa.refresh_from_db()
        self.assertEqual(hoa.annotation, "Original annotation")

    def test_retrieve_communication_notes_success(self):
        """Test retrieving communication notes for a homeowner association."""
        hoa = baker.make(HomeownerAssociation)
        older = baker.make(
            HomeownerAssociationCommunicationNote,
            homeowner_association=hoa,
            note="older",
            date=self._get_timezone_now() - self._get_timezone_delta(days=2),
        )
        middle = baker.make(
            HomeownerAssociationCommunicationNote,
            homeowner_association=hoa,
            note="middle",
            date=self._get_timezone_now() - self._get_timezone_delta(days=1),
        )
        newest = baker.make(
            HomeownerAssociationCommunicationNote,
            homeowner_association=hoa,
            note="newest",
            date=self._get_timezone_now(),
        )
        url = reverse("homeownerassociation-communication-notes", args=[hoa.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        returned_ids = [item["id"] for item in response.data]
        self.assertEqual(returned_ids, [newest.id, middle.id, older.id])

    def test_retrieve_communication_notes_empty(self):
        """Test retrieving communication notes when none exist."""
        hoa = baker.make(HomeownerAssociation)
        url = reverse("homeownerassociation-communication-notes", args=[hoa.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_create_communication_note_success(self):
        """Test creating a communication note for a homeowner association."""
        hoa = baker.make(HomeownerAssociation)
        url = reverse("homeownerassociation-communication-notes", args=[hoa.id])
        data = {"note": "Initial note", "author_name": "Alice"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["note"], "Initial note")
        self.assertEqual(response.data["author_name"], "Alice")
        self.assertEqual(
            HomeownerAssociationCommunicationNote.objects.filter(
                homeowner_association=hoa
            ).count(),
            1,
        )

    def test_create_communication_note_invalid(self):
        """Test creating a communication note with invalid data."""
        hoa = baker.make(HomeownerAssociation)
        url = reverse("homeownerassociation-communication-notes", args=[hoa.id])
        response = self.client.post(url, {"author_name": "Bob"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_update_communication_note_success(self):
        """Test updating a communication note for a homeowner association."""
        hoa = baker.make(HomeownerAssociation)
        note = baker.make(
            HomeownerAssociationCommunicationNote,
            homeowner_association=hoa,
            note="Old",
            author_name="A",
        )
        url = reverse(
            "homeownerassociation-communication-note-detail", args=[hoa.id, note.id]
        )
        data = {"note": "New text", "author_name": "Alice"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.note, "New text")
        self.assertEqual(note.author_name, "Alice")

    def test_delete_communication_note_success(self):
        """Test deleting a communication note for a homeowner association."""
        hoa = baker.make(HomeownerAssociation)
        note = baker.make(
            HomeownerAssociationCommunicationNote,
            homeowner_association=hoa,
            note="To delete",
            author_name="A",
        )
        url = reverse(
            "homeownerassociation-communication-note-detail", args=[hoa.id, note.id]
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            HomeownerAssociationCommunicationNote.objects.filter(id=note.id).count(), 0
        )

    def test_delete_communication_note_not_found(self):
        """Test deleting a non-existent communication note."""
        hoa = baker.make(HomeownerAssociation)
        url = reverse(
            "homeownerassociation-communication-note-detail", args=[hoa.id, 999]
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)

    def _get_timezone_now(self):
        """Helper method to get current timezone-aware datetime."""
        from django.utils import timezone

        return timezone.now()

    def _get_timezone_delta(self, **kwargs):
        """Helper method to create timezone-aware timedelta."""
        from django.utils import timezone

        return timezone.timedelta(**kwargs)
