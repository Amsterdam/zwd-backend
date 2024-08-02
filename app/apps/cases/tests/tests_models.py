from django.core import management
from django.test import TestCase

from apps.cases.models import Case
from model_bakery import baker

class CaseModelTest(TestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()
    def test_can_create_case(self):
        """A case can be created"""
        self.assertEqual(Case.objects.count(), 0)
        baker.make(Case)
        self.assertEqual(Case.objects.count(), 1)