import copy
import datetime
import os
from functools import lru_cache


from apps.users import auth
from apps.events.models import CaseEvent, TaskModelEventEmitter
from apps.cases.models import Case, CaseStatus
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from SpiffWorkflow import TaskState
from SpiffWorkflow.bpmn.script_engine import PythonScriptEngine, TaskDataEnvironment
from SpiffWorkflow.bpmn.serializer import BpmnWorkflowSerializer
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.camunda.parser.CamundaParser import CamundaParser
from SpiffWorkflow.camunda.serializer.config import CAMUNDA_CONFIG
from SpiffWorkflow.camunda.specs.user_task import UserTask
from SpiffWorkflow.camunda.specs.event_definitions import MessageEventDefinition
from SpiffWorkflow.bpmn import BpmnEvent
from SpiffWorkflow.bpmn.specs.event_definitions.timer import TimerEventDefinition
from .managers import BulkCreateSignalsManager
from .tasks import (
    task_complete_user_task_and_create_new_user_tasks,
    task_script_wait,
)
from .utils import get_initial_data_from_config
from django.utils.timezone import make_aware
from django.db import transaction


class CaseWorkflow(models.Model):

    WORKFLOW_TYPE_SUB = "sub_workflow"

    parent_workflow = models.ForeignKey(
        to="workflow.CaseWorkflow",
        related_name="child_workflows",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    case = models.ForeignKey(
        to=Case,
        related_name="workflows",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    workflow_type = models.CharField(
        max_length=100,
        null=True,
    )
    workflow_version = models.CharField(
        max_length=100,
        null=True,
    )
    workflow_theme_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    workflow_message_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    data = models.JSONField(null=True)
    serializer = BpmnWorkflowSerializer
    main_workflow = models.BooleanField(
        default=False,
    )
    serialized_workflow_state = models.JSONField(null=True)
    started = models.BooleanField(
        default=False,
    )

    completed = models.BooleanField(
        default=False,
    )

    def __str__(self):
        return f"W: {self.id}, C: {self.case.id}"

    def start(self):
        workflow = self._get_or_restore_workflow_state()
        initial_data = get_initial_data_from_config(
            self.workflow_theme_name,
            self.workflow_type,
            self.workflow_version,
            self.workflow_message_name,
        )
        initial_data.update(self.data)
        workflow = self._initial_data(workflow, initial_data)
        if self.workflow_message_name:
            self._handle_workflow_event(workflow, self.workflow_message_name)

        workflow = self.update_workflow(workflow)
        return

    def complete_user_task_and_create_new_user_tasks(self, task_id=None, data=None):
        workflow = self._get_or_restore_workflow_state()
        if not workflow:
            return

        task = workflow.get_task_from_id(task_id)
        if task and isinstance(task.task_spec, UserTask):
            task.set_data(**data)
            task.complete()

        workflow = self.update_workflow(workflow)
        self._update_db(workflow)

    def has_a_timer_event_fired(self):
        wf = self._get_or_restore_workflow_state()
        if not wf:
            return False
        waiting_tasks = wf.get_tasks(state=TaskState.WAITING)
        for task in waiting_tasks:
            if hasattr(task.task_spec, "event_definition") and isinstance(
                task.task_spec.event_definition, TimerEventDefinition
            ):
                event_definition = task.task_spec.event_definition
                has_fired = event_definition.has_fired(task)
                if has_fired:
                    print(
                        f"TimerEventDefinition for task '{task.task_spec.name}' has expired. Workflow with id '{self.id}', needs an update"
                    )
                    return True
        return False

    def _handle_workflow_event(self, workflow, message_name):
        workflow.refresh_waiting_tasks()
        workflow.do_engine_steps()
        # Only the message name is relevant here, the other parameters are not used but the docs don't really specify what they are used for.
        workflow.catch(
            BpmnEvent(
                MessageEventDefinition(message_name),
                {"result_var": "result_var", "payload": "payload"},
            )
        )

    @staticmethod
    def _get_workflow_path(workflow_type, workflow_version, theme_name="default"):
        """
        Get the filesystem path for a workflow's BPMN files.
        """
        path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "bpmn_files",
            theme_name.lower(),
            workflow_type.lower(),
            workflow_version.lower(),
        )
        return path

    def _set_case_status(self, state_name):
        self.case.status, _ = CaseStatus.objects.get_or_create(
            name=state_name,
        )
        self.case.save()

    def _save_workflow_state(self, wf):
        if wf.last_task:
            self.data.update(wf.last_task.data)

        if wf.is_completed() and not self.completed:
            self.completed = True
        reg = self.serializer().configure(CAMUNDA_CONFIG)
        serializer = BpmnWorkflowSerializer(registry=reg)
        state = serializer.serialize_json(wf)
        self.serialized_workflow_state = state
        self.started = True
        self.save()

        if self.completed and self.parent_workflow:
            parent_workflow = CaseWorkflow.objects.get(id=self.parent_workflow.id)
            data = copy.deepcopy(wf.last_task.data) if wf.last_task else {}
            if parent_workflow and parent_workflow.workflow_type == "director":
                parent_workflow.data.update(data)
                wf = parent_workflow._get_or_restore_workflow_state()
                self._handle_workflow_event(wf, f"resume_after_{self.workflow_type}")
                parent_workflow.update_workflow(wf)
                parent_workflow.data.update(data)
                parent_workflow.save()

    def _update_tasks(self, wf):
        self._set_obsolete_tasks_to_completed(wf)
        self._create_user_tasks(wf)
        self._complete_sub_workflow(wf)

    # The sub_workflow.bpmn has multiple flows inside, so spiff does not know when the workflow is completed.
    def _complete_sub_workflow(self, wf):
        if (
            self.workflow_type == self.WORKFLOW_TYPE_SUB
            and len(wf.get_tasks(state=TaskState.READY)) == 0
        ):
            self.completed = True
            self.save()

    def _create_user_tasks(self, wf):
        ready_tasks = wf.get_tasks(state=TaskState.READY)
        task_data = [
            CaseUserTask(
                task_id=task.id,
                task_name=task.task_spec.name,
                name=task.task_spec.bpmn_name,
                roles=[r.strip() for r in task.task_spec.lane.split(",")],
                form=self._parse_task_spec_form(task.task_spec.form),
                due_date=make_aware(datetime.datetime.today()),
                case=self.case,
                workflow=self,
                initiated_by=(
                    auth.get_user_model().objects.get(id=self.data.get("initiated_by"))
                    if self.data.get("initiated_by")
                    else None
                ),
                requires_review=task.task_spec.extensions.get("requires_review", False)
                or False,
            )
            for task in ready_tasks
            if not CaseUserTask.objects.filter(
                task_name=task.task_spec.name,
                workflow=self,
            )
        ]
        task_instances = CaseUserTask.objects.bulk_create(task_data)
        return task_instances

    def _evaluate_form_field_label(self, label):
        expression = label.replace("{{", "{").replace("}}", "}")
        return expression.format(workflow=self)

    def _parse_task_spec_form(self, form):
        trans_types = {
            "enum": "select",
            "boolean": "checkbox",
            "string": "text",
            "long": "number",
            "expression": "expression",
            "file": "file",
            "advisor": "advisor",
            "date": "date",
            "close_case": "close_case",
        }
        fields = [
            {
                "label": self._evaluate_form_field_label(f.label),
                "options": [
                    {
                        "value": o.id,
                        "label": o.name,
                    }
                    for o in f.__dict__.get("options", [])
                ],
                "name": f.id,
                "type": (
                    "multiselect"
                    if bool([v.name for v in f.validation if v.name == "multiple"])
                    else trans_types.get(f.type, "text")
                ),
                "required": not bool(
                    [v.name for v in f.validation if v.name == "optional"]
                ),
                "tooltip": next(
                    iter([v.value for v in f.properties if v.id == "tooltip"]), None
                ),
            }
            for f in form.fields
        ]
        return fields

    def _set_obsolete_tasks_to_completed(self, wf):
        ready_tasks_ids = [t.id for t in wf.get_tasks(state=TaskState.READY)]
        task_instances = self.tasks.all().exclude(
            task_id__in=ready_tasks_ids,
        )
        updated = task_instances.update(completed=True)
        return updated

    def _initial_data(self, wf, data):
        first_task = wf.get_tasks(state=TaskState.READY)
        last_task = wf.last_task
        if first_task:
            first_task = first_task[0]
        elif last_task:
            first_task = last_task
        first_task.data.update(data)
        return wf

    def update_workflow(self, wf):
        wf.refresh_waiting_tasks()
        wf.do_engine_steps()
        self._update_db(wf)
        return wf

    def _update_db(self, wf):
        self._save_workflow_state(wf)
        self._update_tasks(wf)

    @staticmethod
    @lru_cache(maxsize=256)
    def _get_workflow_spec(workflow_type, workflow_version, theme_name="default"):
        """
        Parse and cache BPMN workflow spec.
        We're caching since reading and parsing BPMN files from the filesystem is a slow operation,
        and versions should never change.
        """
        parser = CamundaParser()
        path = CaseWorkflow._get_workflow_path(
            workflow_type,
            workflow_version,
            theme_name,
        )
        for f in CaseWorkflow._get_workflow_spec_files(path):
            parser.add_bpmn_file(f)
        return parser.get_spec(workflow_type)

    def _get_or_restore_workflow_state(self):
        """
        Gets the unserialized workflow from this workflow instance, it has to use an workflow_spec,
        which in this case will be loaded from the filesystem.
        """
        theme_name = self.workflow_theme_name or "default"
        workflow_spec = self._get_workflow_spec(
            self.workflow_type, self.workflow_version, theme_name
        )
        if not workflow_spec:
            return
        if self.serialized_workflow_state:
            reg = self.serializer().configure(CAMUNDA_CONFIG)
            serializer = BpmnWorkflowSerializer(registry=reg)
            workflow = serializer.deserialize_json(self.serialized_workflow_state)
            workflow = self._get_script_engine(workflow)
            return workflow
        else:
            workflow = BpmnWorkflow(workflow_spec)
            workflow = self._get_script_engine(workflow)
            return workflow

    @staticmethod
    def _get_workflow_spec_files(path):
        if not os.path.isdir(path):
            return []
        return [
            os.path.join(path, f)
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and CaseWorkflow._is_bpmn_file(f)
        ]

    def _start_child_workflow(
        self, subworkflow_name, parent_workflow_id, extra_data={}
    ):
        from apps.workflow.models import CaseWorkflow

        parent_workflow = CaseWorkflow.objects.get(id=parent_workflow_id)
        with transaction.atomic():
            data = copy.deepcopy(parent_workflow.data)
            data.update(extra_data)
            subworkflow = CaseWorkflow.objects.create(
                case=parent_workflow.case,
                parent_workflow=(
                    parent_workflow if subworkflow_name != "close_case" else None
                ),
                workflow_type=subworkflow_name,
                data=data,
            )
            subworkflow.start()

    @staticmethod
    def _is_bpmn_file(file_name):
        return file_name.split(".")[-1] == "bpmn"

    def _get_script_engine(self, wf):
        # injects functions in workflow
        workflow_instance = self

        def set_status(input):
            workflow_instance._set_case_status(input)

        def script_wait(message, data={}):
            task_script_wait.delay(workflow_instance.id, message, data)

        def start_workflow(subworkflow_name, data={}):
            self._start_child_workflow(subworkflow_name, workflow_instance.id, data)

        def close_case():
            workflow_instance.case.close_case()

        def get_data(field_name):
            return self.data.get(field_name, {}).get("value")

        def parse_duration_string(str_duration):
            # If the environment is not production, the duration is set to 2 minutes for testing purposes
            if settings.ENVIRONMENT != "production":
                two_minutes_iso_8601 = "T120S"
                return two_minutes_iso_8601
            return str_duration

        wf.script_engine = PythonScriptEngine(
            environment=TaskDataEnvironment(
                environment_globals={
                    "set_status": set_status,
                    "script_wait": script_wait,
                    "start_workflow": start_workflow,
                    "parse_duration": parse_duration_string,
                    "close_case": close_case,
                    "get_data": get_data,
                }
            )
        )
        return wf

    @staticmethod
    def complete_user_task(id, data, wait=False):
        task = task_complete_user_task_and_create_new_user_tasks.delay(id, data)
        if wait:
            task.wait(timeout=None, interval=0.5)


class CaseUserTask(models.Model):
    completed = models.BooleanField(
        default=False,
    )
    # connects spiff task with this db task
    task_id = models.UUIDField(
        unique=True,
    )
    # name of the task_spec in spiff, in bpmn modeler is this the id field
    task_name = models.CharField(
        max_length=255,
    )
    # description of the task_spec in spiff, in bpmn modeler is this the name field
    name = models.CharField(
        max_length=255,
    )
    form = models.JSONField(
        default=list,
        null=True,
        blank=True,
    )
    roles = ArrayField(
        base_field=models.CharField(max_length=255),
        default=list,
        null=True,
        blank=True,
    )
    due_date = models.DateTimeField()
    owner = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    case = models.ForeignKey(
        to=Case,
        related_name="tasks",
        on_delete=models.CASCADE,
    )
    workflow = models.ForeignKey(
        to=CaseWorkflow,
        related_name="tasks",
        on_delete=models.CASCADE,
    )
    initiated_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="case_user_tasks",
        on_delete=models.PROTECT,
        null=True,
    )
    objects = BulkCreateSignalsManager()
    requires_review = models.BooleanField(
        default=False,
        help_text="Indicates whether this task requires review by another user.",
    )

    def complete(self):
        self.completed = True
        self.save()


class GenericCompletedTask(TaskModelEventEmitter):
    EVENT_TYPE = CaseEvent.TYPE_GENERIC_TASK
    case_user_task_id = models.CharField(max_length=255, default="-1")

    case = models.ForeignKey(
        to=Case,
        related_name="generic_completed_tasks",
        on_delete=models.CASCADE,
    )
    date_added = models.DateTimeField(auto_now_add=True)
    task_name = models.CharField(
        max_length=255,
    )
    description = models.TextField()
    author = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="generic_completed_tasks",
        on_delete=models.PROTECT,
    )
    variables = models.JSONField(null=True)

    def __get_event_values__(self):
        variables = self.variables.get("mapped_form_data", {}) or self.variables
        return {
            "author": self.author.__str__(),
            "date_added": self.date_added,
            "description": self.description,
            "variables": variables,
        }


class WorkflowOption(models.Model):
    name = models.CharField(max_length=255)
    message_name = models.CharField(max_length=255)
    enabled_on_case_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.message_name}"

    class Meta:
        ordering = ["name"]


class CaseWorkflowStateHistory(models.Model):
    workflow = models.ForeignKey(
        CaseWorkflow,
        related_name="state_history",
        on_delete=models.CASCADE,
    )

    serialized_workflow_state = models.JSONField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def get_tasks_to_create(self):
        return [t.task_spec.bpmn_name for t in self._get_ready_tasks()]

    def get_task_to_delete(self):
        return list(
            self.workflow.tasks.filter(completed=False).values_list("name", flat=True)
        )

    def restore(self):
        with transaction.atomic():
            workflow = self.workflow
            wf = self._restore_workflow_state(persist=True)

            workflow.tasks.filter(completed=False).delete()

            ready_task_ids = [t.id for t in wf.get_tasks(state=TaskState.READY)]
            CaseUserTask.objects.filter(task_id__in=ready_task_ids).delete()

            workflow._create_user_tasks(wf)

    def _restore_workflow_state(self, persist=False):
        workflow = self.workflow
        workflow.serialized_workflow_state = self.serialized_workflow_state
        workflow.data = self.data

        if persist:
            workflow.save(update_fields=["serialized_workflow_state", "data"])

        return workflow._get_or_restore_workflow_state()

    def _get_ready_tasks(self):
        wf = self._restore_workflow_state()
        return wf.get_tasks(state=TaskState.READY)
