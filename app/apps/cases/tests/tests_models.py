from apps.homeownerassociation.models import HomeownerAssociation
from apps.cases.models import AdviceType, Case
from django.core import management
from django.test import TestCase
from model_bakery import baker
from apps.workflow.models import CaseWorkflow


class CaseModelTest(TestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()

    def test_can_create_case(self):
        self.assertEqual(Case.objects.count(), 0)
        baker.make(Case)
        self.assertEqual(Case.objects.count(), 1)

    def test_close_case(self):
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        baker.make(CaseWorkflow, case=case, workflow_type="sub_workflow")
        self.assertEqual(Case.objects.count(), 1)
        self.assertEqual(CaseWorkflow.objects.count(), 1)
        case.close_case()
        self.assertIsNotNone(case.end_date)
        self.assertEqual(Case.objects.count(), 1)
        self.assertEqual(Case.objects.filter(end_date__isnull=False).count(), 1)
        self.assertEqual(Case.objects.filter(end_date__isnull=True).count(), 0)
        self.assertEqual(CaseWorkflow.objects.count(), 0)
