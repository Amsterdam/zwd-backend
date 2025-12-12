from apps.homeownerassociation.models import HomeownerAssociation
from apps.cases.models import AdviceType, ApplicationType, Case
from django.core import management
from django.test import TestCase
from model_bakery import baker
from apps.workflow.models import CaseWorkflow, GenericCompletedTask


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

    def test_prefixed_dossier_id_for_course(self):
        """Test that Course cases get CUR prefix"""
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            application_type=ApplicationType.COURSE.value,
            advice_type=None,
        )
        expected_prefix = f"{case.id}CUR"
        self.assertEqual(case.prefixed_dossier_id, expected_prefix)

    def test_prefixed_dossier_id_for_activation_team(self):
        """Test that ActivationTeam cases get ACT prefix"""
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            application_type=ApplicationType.ACTIVATIONTEAM.value,
            advice_type=None,
        )
        expected_prefix = f"{case.id}ACT"
        self.assertEqual(case.prefixed_dossier_id, expected_prefix)

    def test_prefixed_dossier_id_for_hbo(self):
        """Test that HBO cases get HBO prefix"""
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            application_type=ApplicationType.ADVICE.value,
            advice_type=AdviceType.HBO.value,
        )
        expected_prefix = f"{case.id}HBO"
        self.assertEqual(case.prefixed_dossier_id, expected_prefix)

    def test_prefixed_dossier_id_for_energy_advice_small_hoa(self):
        """Test that Energy Advice for small HOA gets EAK prefix"""
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=10
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            application_type=ApplicationType.ADVICE.value,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        expected_prefix = f"{case.id}EAK"
        self.assertEqual(case.prefixed_dossier_id, expected_prefix)

    def test_prefixed_dossier_id_for_energy_advice_large_hoa(self):
        """Test that Energy Advice for large HOA gets EAG prefix"""
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=20
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            application_type=ApplicationType.ADVICE.value,
            advice_type=AdviceType.ENERGY_ADVICE.value,
        )
        expected_prefix = f"{case.id}EAG"
        self.assertEqual(case.prefixed_dossier_id, expected_prefix)

    def test_course_case_has_no_advice_type(self):
        """Test that Course cases should not have advice_type set"""
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            application_type=ApplicationType.COURSE.value,
            advice_type=None,
        )
        self.assertIsNone(case.advice_type)
        self.assertEqual(case.application_type, ApplicationType.COURSE.value)

    def test_get_additional_report_fields(self):
        homeowner_association = baker.make(
            HomeownerAssociation, number_of_apartments=13
        )
        case = baker.make(
            Case,
            homeowner_association=homeowner_association,
            application_type=ApplicationType.COURSE.value,
            advice_type=None,
        )
        generic_completed_task = baker.make(
            GenericCompletedTask,
            case=case,
            task_name="some_task",
            variables={"mapped_form_data": {}},
        )
