from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from utils.test_utils import (
    create_case,
    get_authenticated_client,
    get_unauthenticated_client,
)


class CaseEventGetAPITest(APITestCase):
    def test_unauthenticated_get(self):
        url = reverse("cases-events", kwargs={"pk": 1})
        client = get_unauthenticated_client()
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_get_no_case(self):
        url = reverse("cases-detail", kwargs={"pk": 1})
        client = get_authenticated_client()
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_get_events(self):
        case = create_case()
        url = reverse("cases-detail", kwargs={"pk": case.id})
        client = get_authenticated_client()
        response = client.get(url)
        self.assertEqual(case.id, response.data.get("id"))
