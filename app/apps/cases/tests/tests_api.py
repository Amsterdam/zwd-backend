from django.core import management
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from utils.test_utils import get_authenticated_client, get_unauthenticated_client


class CaseApiTest(APITestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()
        self.client = get_authenticated_client()

    def test_unauthenticated_get(self):
        url = reverse("cases-list")
        client = get_unauthenticated_client()
        get_authenticated_client()
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_get(self):
        url = reverse("cases-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_get_empty(self):
        url = reverse("cases-list")
        response = self.client.get(url)
        data = response.json()

        self.assertEqual(data, [])

    def test_retrieve_case(self):
        self._create_case()
        case_id = 1
        url = reverse("cases-detail", args=[case_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def _create_case(self):
        url = reverse("cases-list")
        data = {"description": "Test case description"}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
