"""
Tests for CaseEvent & EventsEmitter models
"""

from django.test import TestCase
from utils.test_utils import create_case, create_completed_task
from apps.events.models import CaseEvent


class CaseEventTest(TestCase):
    def test_case_creates_events(self):
        self.assertEqual(0, CaseEvent.objects.count())
        create_case()
        case_event_task = CaseEvent.objects.get(type=CaseEvent.TYPE_CASE)
        self.assertTrue(case_event_task)

    def test_completed_task_creates_events(self):
        self.assertEqual(0, CaseEvent.objects.count())
        create_completed_task()
        case_event_task = CaseEvent.objects.get(type=CaseEvent.TYPE_GENERIC_TASK)
        self.assertTrue(case_event_task)
