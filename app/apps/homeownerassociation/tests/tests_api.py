from django.urls import reverse
from rest_framework.test import APITestCase
from django.core import management
from model_bakery import baker
from apps.cases.models import Case
from utils.test_utils import get_authenticated_client
from apps.homeownerassociation.models import (
    Contact,
    District,
    HomeownerAssociation,
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
        district = baker.make(District, name="Test District")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), District.objects.count())
        self.assertEqual(response.data[0], district.name)

    def test_retrieve_wijken(self):
        url = reverse("wijk-list")
        wijk = baker.make(Wijk, name="Test wijk")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), Wijk.objects.count())
        self.assertEqual(response.data[0], wijk.name)

    def test_get_hoa_contacts(self):
        hoa = baker.make(HomeownerAssociation)
        contact1 = baker.make(Contact)
        contact1.homeowner_associations.add(hoa)
        contact2 = baker.make(Contact)
        contact2.homeowner_associations.add(hoa)
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
                "role": "President",
            },
        ]
        url = reverse("homeownerassociation-contacts", args=[hoa.id])
        response = self.client.put(url, {"contacts": contact_data}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["detail"], "Contacts added successfully")

    def test_put_hoa_contacts_with_empty_data(self):
        hoa = baker.make("homeownerassociation.HomeownerAssociation")
        url = reverse("homeownerassociation-contacts", args=[hoa.id])
        response = self.client.put(url, {"contacts": []}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "At least one contact is required")

    def test_delete_contact_shared_not_deleted(self):
        hoa1 = baker.make(HomeownerAssociation)
        hoa2 = baker.make(HomeownerAssociation)
        contact = baker.make(Contact)
        contact.homeowner_associations.set([hoa1, hoa2])

        url = reverse("homeownerassociation-delete", args=[hoa1.id, contact.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        contact.refresh_from_db()
        self.assertIn(hoa2, contact.homeowner_associations.all())
        self.assertNotIn(hoa1, contact.homeowner_associations.all())

    def test_delete_contact_exclusive_deleted(self):
        hoa = baker.make(HomeownerAssociation)
        contact = baker.make(Contact)
        contact.homeowner_associations.set([hoa])

        url = reverse("homeownerassociation-delete", args=[hoa.id, contact.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        with self.assertRaises(Contact.DoesNotExist):
            Contact.objects.get(id=contact.id)
