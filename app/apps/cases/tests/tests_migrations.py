from datetime import datetime
from importlib import import_module
from apps.advisor.models import Advisor
from apps.cases.models import Case
from apps.workflow.models import GenericCompletedTask
from django.apps import apps
from django.core import management
from django.test import TestCase
from django.utils import timezone
from model_bakery import baker

backfill_migration = import_module(
    "apps.cases.migrations.0031_backfill_advisor_assigned_at"
)


class BackfillAdvisorAssignedAtTest(TestCase):
    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()

    def _complete_task(self, case, task_name, date_added):
        task = baker.make(GenericCompletedTask, case=case, task_name=task_name)
        # date_added uses auto_now_add, so override it afterwards
        GenericCompletedTask.objects.filter(id=task.id).update(date_added=date_added)

    def test_uses_date_of_latest_advisor_task(self):
        case = baker.make(Case, advisor=baker.make(Advisor))
        first = timezone.make_aware(datetime(2025, 3, 1, 10, 0))
        latest = timezone.make_aware(datetime(2025, 5, 1, 10, 0))
        self._complete_task(case, backfill_migration.ADVISOR_TASK_NAME, first)
        self._complete_task(case, backfill_migration.ADVISOR_TASK_NAME, latest)
        self._complete_task(case, "other_task", timezone.now())

        backfill_migration.backfill_advisor_assigned_at(apps, None)

        self.assertEqual(Case.objects.get(id=case.id).advisor_assigned_at, latest)

    def test_keeps_empty_date_without_advisor_task(self):
        case = baker.make(Case, advisor=baker.make(Advisor))

        backfill_migration.backfill_advisor_assigned_at(apps, None)

        self.assertIsNone(Case.objects.get(id=case.id).advisor_assigned_at)

    def test_skips_case_without_advisor(self):
        case = baker.make(Case, advisor=None)
        self._complete_task(case, backfill_migration.ADVISOR_TASK_NAME, timezone.now())

        backfill_migration.backfill_advisor_assigned_at(apps, None)

        self.assertIsNone(Case.objects.get(id=case.id).advisor_assigned_at)

    def test_keeps_existing_date(self):
        assigned_at = timezone.make_aware(datetime(2024, 1, 1, 10, 0))
        case = baker.make(
            Case, advisor=baker.make(Advisor), advisor_assigned_at=assigned_at
        )
        self._complete_task(case, backfill_migration.ADVISOR_TASK_NAME, timezone.now())

        backfill_migration.backfill_advisor_assigned_at(apps, None)

        self.assertEqual(Case.objects.get(id=case.id).advisor_assigned_at, assigned_at)
