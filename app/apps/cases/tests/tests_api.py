from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.core import management
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

class CaseApiTest(APITestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()
        self.client = get_authenticated_client()

    def test_unauthenticated_get(self):
        url = reverse("cases-list")
        client = get_unauthenticated_client()
        get_authenticated_client()
        print(url)
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
        url = reverse('cases-detail', args=[case_id])
        print(url)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def _create_case(self):
        url = reverse('cases-list')
        data = {
            'description': 'Test case description'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

def get_unauthenticated_client():
    """
    Returns an unauthenticated APIClient, for unit testing API requests
    """
    return APIClient()

def get_authenticated_client():
    """
    Returns an authenticated APIClient, for unit testing API requests
    """
    user = get_test_user()
    access_token = RefreshToken.for_user(user).access_token
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer {}".format(access_token))
    return client
def get_test_user():
    """
    Creates and returns a test user
    """
    return get_user_model().objects.get_or_create(email="admin@admin.com")[0]