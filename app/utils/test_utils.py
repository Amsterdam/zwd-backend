from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from model_bakery import baker
from apps.workflow.models import GenericCompletedTask
from apps.cases.models import Case


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


def create_case():
    case = baker.make(Case)
    return case


def create_completed_task():
    task = baker.make(GenericCompletedTask)
    return task
