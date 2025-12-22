from apps.homeownerassociation.models import HomeownerAssociation
from apps.cases.models import Case
from apps.workflow.models import CaseWorkflow, CaseWorkflowStateHistory
from django.core import management
from django.test import TestCase
from model_bakery import baker
from SpiffWorkflow import TaskState


class WorkflowModelTest(TestCase):

    def setUp(self):
        management.call_command("flush", verbosity=0, interactive=False)
        super().setUp()

    def test_case_workflow_state_history_creation(self):
        case = self._make_case()

        wf_state = "{'state': 'initial'}"
        workflow = baker.make(
            CaseWorkflow,
            case=case,
            completed=False,
            workflow_type="sub_workflow",
            serialized_workflow_state=wf_state,
        )

        workflow.serialized_workflow_state = {"key": "value"}
        workflow.save()

        history_qs = CaseWorkflowStateHistory.objects.filter(workflow=workflow)

        self.assertEqual(history_qs.count(), 1)
        self.assertEqual(history_qs.first().serialized_workflow_state, wf_state)

    def test_case_workflow_state_history_restoration(self):
        child_workflow = self._start_director_workflow()

        initial_task_names = self._get_ready_task_names(child_workflow)

        self._complete_all_ready_tasks(child_workflow)

        current_task_names = self._get_ready_task_names(child_workflow)

        history = CaseWorkflowStateHistory.objects.filter(
            workflow=child_workflow
        ).first()

        self.assertNotEqual(
            current_task_names,
            history.get_tasks_to_create(),
        )

        history.restore()
        child_workflow.refresh_from_db()

        restored_task_names = self._get_ready_task_names(child_workflow)

        self.assertEqual(restored_task_names, initial_task_names)

    def test_case_workflow_state_history_get_tasks_to_create(self):
        child_workflow = self._start_director_workflow()

        initial_task_names = self._get_ready_task_names(child_workflow)

        self._complete_all_ready_tasks(child_workflow)

        history = CaseWorkflowStateHistory.objects.filter(
            workflow=child_workflow
        ).first()

        self.assertEqual(initial_task_names, history.get_tasks_to_create())

    def test_case_workflow_state_history_get_tasks_to_delete(self):
        child_workflow = self._start_director_workflow()

        self._complete_all_ready_tasks(child_workflow)

        history = CaseWorkflowStateHistory.objects.filter(
            workflow=child_workflow
        ).first()

        current_task_names = self._get_ready_task_names(child_workflow)

        self.assertEqual(current_task_names, history.get_tasks_to_delete())

    def test_case_workflow_state_history_delete_on_workflow_complete(self):
        child_workflow = self._start_director_workflow()

        self._complete_all_ready_tasks(child_workflow)

        history = CaseWorkflowStateHistory.objects.filter(
            workflow=child_workflow
        ).first()

        self.assertIsNotNone(history)
        child_workflow.completed = True
        child_workflow.save()
        history_qs = CaseWorkflowStateHistory.objects.filter(workflow=child_workflow)
        self.assertFalse(history_qs.exists())

    def _make_case(self):
        hoa = baker.make(
            HomeownerAssociation,
            name="Hoa_name",
            number_of_apartments=12,
        )
        return baker.make(Case, homeowner_association=hoa)

    def _start_director_workflow(self):
        case = self._make_case()
        workflow = baker.make(
            CaseWorkflow,
            case=case,
            completed=False,
            workflow_type="director",
        )
        workflow.start()
        return CaseWorkflow.objects.filter(parent_workflow=workflow).first()

    def _get_ready_tasks(self, workflow):
        wf = workflow._get_or_restore_workflow_state()
        return wf.get_tasks(state=TaskState.READY)

    def _get_ready_task_names(self, workflow):
        return [task.task_spec.bpmn_name for task in self._get_ready_tasks(workflow)]

    def _complete_all_ready_tasks(self, workflow):
        for task in self._get_ready_tasks(workflow):
            workflow.complete_user_task_and_create_new_user_tasks(task.id, {})
        workflow.refresh_from_db()
