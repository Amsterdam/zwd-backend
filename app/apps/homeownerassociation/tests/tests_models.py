from apps.homeownerassociation.models import HomeownerAssociation
from django.core import management
from django.test import TestCase
from model_bakery import baker


class HomeownerAssociationTest(TestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()

    def test_can_create_hoa(self):
        """A case can be created"""
        self.assertEqual(HomeownerAssociation.objects.count(), 0)
        baker.make(HomeownerAssociation)
        self.assertEqual(HomeownerAssociation.objects.count(), 1)
