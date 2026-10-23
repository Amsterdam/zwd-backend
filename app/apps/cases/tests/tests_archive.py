from datetime import date
from unittest.mock import patch
from apps.cases.archive import build_archive_plan, execute_archive_plan
from apps.cases.models import ActivationTeam, Case, CaseClose, CaseDocument
from apps.cases.tests.tests_admin import make_closed_case
from apps.events.models import CaseEvent
from apps.homeownerassociation.models import (
    Contact,
    HomeownerAssociation,
    HomeownerAssociationCommunicationNote,
)
from apps.workflow.models import CaseUserTask, CaseWorkflow, GenericCompletedTask
from django.contrib.admin import helpers
from django.contrib.auth import get_user_model
from django.core import management
from django.test import TestCase
from django.utils import timezone
from model_bakery import baker

TODAY = date(2028, 1, 1)


class ArchiveTestCase(TestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()

    def make_hoa(self, **kwargs):
        return baker.make(HomeownerAssociation, number_of_apartments=13, **kwargs)

    def make_expired_case(self, hoa=None):
        return make_closed_case(
            False, date(2020, 1, 1), homeowner_association=hoa or self.make_hoa()
        )


class ArchiveCaseTest(ArchiveTestCase):
    def setUp(self):
        super().setUp()
        self.hoa = self.make_hoa()
        self.case = self.make_expired_case(self.hoa)
        workflow = baker.make(
            CaseWorkflow, case=self.case, workflow_type="sub_workflow"
        )
        baker.make(CaseUserTask, case=self.case, workflow=workflow)
        baker.make(CaseDocument, case=self.case, document="uploads/cases/1/a.pdf")
        baker.make(GenericCompletedTask, case=self.case, variables={})
        baker.make(ActivationTeam, case=self.case, subject="Onderwerp")
        baker.make(
            HomeownerAssociationCommunicationNote, homeowner_association=self.hoa
        )
        baker.make(Contact, homeowner_association=self.hoa)

    @patch("apps.cases.archive.default_storage")
    def test_archive_deletes_case_data(self, storage):
        self.assertTrue(CaseEvent.objects.filter(case=self.case).exists())
        plan = build_archive_plan(Case.objects.all(), TODAY)

        with self.captureOnCommitCallbacks(execute=True):
            counts = execute_archive_plan(plan)

        self.assertEqual(counts["documents"], 1)
        self.assertEqual(counts["contacts"], 1)
        self.assertFalse(CaseWorkflow.objects.filter(case=self.case).exists())
        self.assertFalse(CaseUserTask.objects.filter(case=self.case).exists())
        self.assertFalse(CaseDocument.objects.filter(case=self.case).exists())
        self.assertFalse(GenericCompletedTask.objects.filter(case=self.case).exists())
        self.assertFalse(CaseEvent.objects.filter(case=self.case).exists())
        self.assertFalse(
            Contact.objects.filter(homeowner_association=self.hoa).exists()
        )
        storage.delete.assert_called_once_with("uploads/cases/1/a.pdf")

    @patch("apps.cases.archive.default_storage")
    def test_archive_keeps_metadata(self, storage):
        plan = build_archive_plan(Case.objects.all(), TODAY)
        execute_archive_plan(plan)

        case = Case.objects.get(id=self.case.id)
        self.assertIsNotNone(case.archived_at)
        self.assertTrue(CaseClose.objects.filter(case=case).exists())
        self.assertEqual(ActivationTeam.objects.get(case=case).subject, "Onderwerp")
        self.assertTrue(HomeownerAssociation.objects.filter(id=self.hoa.id).exists())
        self.assertTrue(
            HomeownerAssociationCommunicationNote.objects.filter(
                homeowner_association=self.hoa
            ).exists()
        )

    @patch("apps.cases.archive.default_storage")
    def test_files_are_not_deleted_when_transaction_is_rolled_back(self, storage):
        plan = build_archive_plan(Case.objects.all(), TODAY)
        with patch(
            "apps.cases.archive.CaseEvent.objects.filter", side_effect=Exception
        ):
            with self.assertRaises(Exception):
                with self.captureOnCommitCallbacks(execute=True):
                    execute_archive_plan(plan)

        storage.delete.assert_not_called()
        self.assertTrue(CaseDocument.objects.filter(case=self.case).exists())
        self.assertIsNone(Case.objects.get(id=self.case.id).archived_at)


class BuildArchivePlanTest(ArchiveTestCase):
    def test_skipped_cases(self):
        expired = self.make_expired_case()
        not_expired = make_closed_case(False, date(2027, 6, 1))
        open_case = baker.make(Case, end_date=None)
        archived = self.make_expired_case()
        Case.objects.filter(id=archived.id).update(archived_at=timezone.now())

        plan = build_archive_plan(Case.objects.all(), TODAY)

        self.assertEqual(plan.case_ids, [expired.id])
        self.assertEqual(plan.skipped_not_expired_ids, [not_expired.id])
        self.assertEqual(plan.skipped_open_ids, [open_case.id])
        self.assertEqual(plan.skipped_archived_ids, [archived.id])
        self.assertEqual(plan.skipped_count, 3)

    def test_contacts_kept_when_hoa_has_unarchived_case(self):
        hoa = self.make_hoa()
        case = self.make_expired_case(hoa)
        baker.make(Case, homeowner_association=hoa, end_date=None)
        baker.make(Contact, homeowner_association=hoa)

        plan = build_archive_plan(Case.objects.filter(id=case.id), TODAY)
        self.assertEqual(plan.hoa_ids_keep_contacts, [hoa.id])
        self.assertEqual(plan.hoa_ids_delete_contacts, [])

        execute_archive_plan(plan)
        self.assertTrue(Contact.objects.filter(homeowner_association=hoa).exists())

    def test_contacts_kept_when_other_case_is_expired_but_not_selected(self):
        hoa = self.make_hoa()
        case = self.make_expired_case(hoa)
        self.make_expired_case(hoa)

        plan = build_archive_plan(Case.objects.filter(id=case.id), TODAY)
        self.assertEqual(plan.hoa_ids_keep_contacts, [hoa.id])

    def test_contacts_deleted_when_other_cases_are_archived(self):
        hoa = self.make_hoa()
        case = self.make_expired_case(hoa)
        other = self.make_expired_case(hoa)
        Case.objects.filter(id=other.id).update(archived_at=timezone.now())
        baker.make(Contact, homeowner_association=hoa)

        plan = build_archive_plan(Case.objects.filter(id=case.id), TODAY)
        self.assertEqual(plan.hoa_ids_delete_contacts, [hoa.id])

        execute_archive_plan(plan)
        self.assertFalse(Contact.objects.filter(homeowner_association=hoa).exists())

    def test_contacts_deleted_when_all_cases_of_hoa_are_in_plan(self):
        hoa = self.make_hoa()
        self.make_expired_case(hoa)
        self.make_expired_case(hoa)
        baker.make(Contact, homeowner_association=hoa, _quantity=2)

        plan = build_archive_plan(Case.objects.all(), TODAY)
        self.assertEqual(plan.hoa_ids_delete_contacts, [hoa.id])
        self.assertEqual(plan.counts()["contacts"], 2)

        execute_archive_plan(plan)
        self.assertFalse(Contact.objects.filter(homeowner_association=hoa).exists())


class ArchiveCasesAdminActionTest(ArchiveTestCase):
    url = "/admin/cases/case/"

    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="admin"
        )
        self.client.force_login(user)
        # The admin uses today's date, so use cases that are expired today
        self.case = self.make_expired_case()
        self.running = make_closed_case(True, timezone.localdate())

    def test_dry_run_shows_plan_without_changes(self):
        response = self.client.post(
            self.url,
            {
                "action": "archive_cases",
                "index": 0,
                helpers.ACTION_CHECKBOX_NAME: [self.case.id, self.running.id],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/cases/case/archive_confirmation.html")
        self.assertEqual(response.context["plan"].case_ids, [self.case.id])
        self.assertEqual(
            response.context["plan"].skipped_not_expired_ids, [self.running.id]
        )
        self.assertContains(response, "Bevestigen en archiveren")
        self.assertIsNone(Case.objects.get(id=self.case.id).archived_at)

    @patch("apps.cases.archive.default_storage")
    def test_confirm_archives_cases(self, storage):
        response = self.client.post(
            self.url,
            {
                "action": "archive_cases",
                "post": "yes",
                helpers.ACTION_CHECKBOX_NAME: [self.case.id, self.running.id],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(Case.objects.get(id=self.case.id).archived_at)
        self.assertIsNone(Case.objects.get(id=self.running.id).archived_at)

    @patch("apps.cases.archive.default_storage")
    def test_confirm_with_select_across_archives_all_expired_cases(self, storage):
        other = self.make_expired_case()
        response = self.client.post(
            self.url,
            {
                "action": "archive_cases",
                "post": "yes",
                "select_across": "1",
                helpers.ACTION_CHECKBOX_NAME: [self.case.id],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            set(
                Case.objects.filter(archived_at__isnull=False).values_list(
                    "id", flat=True
                )
            ),
            {self.case.id, other.id},
        )
