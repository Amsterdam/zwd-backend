from apps.cases.models import Case
from apps.workflow.models import CaseWorkflow
from django.core import management
from django.test import TestCase
from model_bakery import baker


class CaseWorkflowTest(TestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()

    def test_can_create_case_workflow(self):
        """A case can be created"""
        self.assertEqual(CaseWorkflow.objects.count(), 0)
        case = baker.make(Case)
        baker.make(CaseWorkflow, case=case, workflow_type="process_vve_ok", data={})
        self.assertEqual(CaseWorkflow.objects.count(), 1)
