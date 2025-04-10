from django.urls import reverse
from rest_framework.test import APITestCase
from django.core import management
from model_bakery import baker
from apps.cases.models import Case
from utils.test_utils import get_authenticated_client
from apps.homeownerassociation.models import District, Wijk


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
