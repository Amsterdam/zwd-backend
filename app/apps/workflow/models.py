import datetime
import json
import os
import re
from string import Template
from django.conf import settings
from django.db import models, transaction
from apps.cases.models import Case
from SpiffWorkflow.camunda.parser.CamundaParser import CamundaParser
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.script_engine import PythonScriptEngine, TaskDataEnvironment
from SpiffWorkflow import TaskState
from SpiffWorkflow.bpmn.specs.mixins.events.event_types import CatchingEvent
from django.utils.dateparse import parse_duration
from SpiffWorkflow.bpmn.serializer import BpmnWorkflowSerializer
from django.contrib.postgres.fields import ArrayField
from .managers import BulkCreateSignalsManager
from .tasks import (
    redis_lock,
    release_lock,
    task_complete_user_task_and_create_new_user_tasks,
    task_complete_worflow,
    task_script_wait,
    task_start_subworkflow,
    task_update_workflow,
    task_wait_for_workflows_and_send_message,
)
from rest_framework.fields import empty
from rest_framework import serializers

class CaseWorkflow(models.Model):
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
    # TODO copy frm aza
    case_state_type = models.CharField(
        max_length=100,
        null=True,
    ) 
    main_workflow = models.BooleanField(
        default=False,
    )

    def start(self):
        parser = CamundaParser()
        path = self.get_workflow_path(self.workflow_type)
        for f in self.get_workflow_spec_files(path):
            parser.add_bpmn_file(f)
        spec = parser.get_spec(self.workflow_type)
        workflow = BpmnWorkflow(spec)
        workflow = self.get_script_engine(workflow)
        initial_data = get_initial_data_from_config(
            self.workflow_theme_name,
            self.workflow_type,
            self.workflow_version,
            self.workflow_message_name,
        )
        success = False
        jump_to = initial_data.pop("jump_to", None)

        #TODO: Figure this out
        # if jump_to:
        #     result = self.reset_subworkflow(jump_to, test=False)
        #     success = result.get("success")

        if not success:
            workflow = self._initial_data(workflow, initial_data)

            workflow = self._update_workflow(workflow)
            #TODO: Figure this out, method is change/gone
            # if self.workflow_message_name:
            #     workflow.message(
            #         self.workflow_message_name,
            #         self.workflow_message_name,
            #         "message_name",
            #     )
            #     workflow = self._update_workflow(workflow)
            self._update_db(workflow)
        return spec


    def get_workflow_spec_files(self, path):
        return [
            os.path.join(path, f)
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and self.is_bpmn_file(f)
        ]

    def is_bpmn_file(self, file_name):
        return file_name.split(".")[-1] == "bpmn"
    

    def get_workflow_path(self, workflow_type, theme_name="default", workflow_version="1.0.0"):
        path = os.path.join(
            self.get_base_path(),
            "bpmn_files",
            theme_name.lower(),
            workflow_type.lower(),
            workflow_version.lower(),
        )
        return path


    def get_base_path(self):
        return os.path.dirname(os.path.realpath(__file__))

    def run_ready_events(self, workflow):
        workflow.refresh_waiting_tasks()
        task = workflow.get_next_task(state=TaskState.READY, spec_class=CatchingEvent)
        while task is not None:
            task.run()
            task = workflow.get_next_task(state=TaskState.READY, spec_class=CatchingEvent)

    
    def get_script_engine(self, wf):
        # injects functions in workflow
        workflow_instance = self

        def set_status(input):
            workflow_instance.set_case_state_type(input)

        def wait_for_workflows_and_send_message(message, data={}):
            task_wait_for_workflows_and_send_message.delay(
                workflow_instance.id, message
            )

        def script_wait(message, data={}):
            task_script_wait.delay(workflow_instance.id, message, data)

        def start_subworkflow(subworkflow_name, data={}):
            task_start_subworkflow.delay(subworkflow_name, workflow_instance.id, data)

        def parse_duration_string(str_duration):
            return parse_duration(str_duration)
        wf.script_engine = PythonScriptEngine(environment=TaskDataEnvironment(environment_globals={
                "set_status": set_status,
                "wait_for_workflows_and_send_message": wait_for_workflows_and_send_message,
                "script_wait": script_wait,
                "start_subworkflow": start_subworkflow,
                "parse_duration": parse_duration_string,
            })
        )
        return wf
    def _initial_data(self, wf, data):

        first_task = wf.get_tasks(state=TaskState.READY)
        last_task = wf.last_task
        if first_task:
            first_task = first_task[0]
        elif last_task:
            first_task = last_task
        first_task.data.update(data)
        return wf

    def _update_workflow(self, wf):
        wf.refresh_waiting_tasks()

        wf.do_engine_steps()

        return wf

    def _update_db(self, wf):
        #TODO: Locks not implemented yet, not sure if required
        # with transaction.atomic():
            self.save_workflow_state(wf)
            self.update_tasks(wf)
            # transaction.on_commit(lambda: self.release_lock())

    def set_case_state_type(self, state_name):
        self.case_state_type = state_name
        self.save()

    def save_workflow_state(self, wf):
        if wf.last_task:
            # update this workflow with the latest task data
            self.data.update(wf.last_task.data)

        completed = False

        if wf.is_completed() and not self.completed:
            completed = True
            self.completed = True
        # TODO: Fix serialize error
        # state = self.serializer().serialize_json(workflow=wf)
        # self.serialized_workflow_state = state
        self.started = True
        self.save()

        #TODO:: Implement
        # if completed:
        #     data = copy.deepcopy(wf.last_task.data) if wf.last_task else {}
        #     task_complete_worflow.delay(self.id, data)

    def update_tasks(self, wf):
        # TODO: Needs tasks first
        # self.set_obsolete_tasks_to_completed(wf)
        self.create_user_tasks(wf)

    def create_user_tasks(self, wf):
        ready_tasks = wf.get_tasks(state=TaskState.READY)
        task_data = [
            CaseUserTask(
                task_id=task.id,
                task_name=task.task_spec.name,
                name=task.task_spec.bpmn_name,
                # roles=[r.strip() for r in task.task_spec.lane.split(",")],
                # form=parse_task_spec_form(task.task_spec.form),
                due_date=datetime.datetime.today(),
                case=self.case,
                workflow=self,
            )
            for task in ready_tasks
            if not CaseUserTask.objects.filter(
                # task_id=task.id,
                task_name=task.task_spec.name,
                workflow=self,
            )
        ]
        task_instances = CaseUserTask.objects.bulk_create(task_data)
        return task_instances

    def set_obsolete_tasks_to_completed(self, wf):
        # some tasks are obsolete after wf.do_engine_steps or wf.refresh_waiting_tasks
        ready_tasks_ids = [t.id for t in wf.get_tasks(state=TaskState.READY)]

        # cleanup: sets dj tasks to completed
        task_instances = self.tasks.all().exclude(
            task_id__in=ready_tasks_ids,
        )
        updated = task_instances.update(completed=True)

        return updated
def get_initial_data_from_config(
    theme_name, workflow_type, workflow_version, message_name=None
):
    validated_workflow_spec_config = validate_workflow_spec(
        settings.WORKFLOW_SPEC_CONFIG
    )
    config = validated_workflow_spec_config.get(theme_name)
    if not config:
        theme_name = "default"
        config = validated_workflow_spec_config.get(theme_name, {})

    config = config.get(workflow_type, {})
    if not config:
        raise Exception(
            f"Workflow type '{workflow_type}', does not exist in this workflow_spec config"
        )
    def pre_serialize_timedelta(value):
        if isinstance(value, datetime.timedelta):
            duration = settings.DEFAULT_WORKFLOW_TIMER_DURATIONS.get(
                settings.ENVIRONMENT
            )
            if duration:
                value = duration
            return json.loads(json.dumps(value, default=str))
        return value

    initial_data = config.get("initial_data", {})

    version = config.get("versions", {}).get(workflow_version)
    if (
        message_name
        and version
        and version.get("messages", {}).get(message_name, {}).get("initial_data", {})
    ):
        initial_data = (
            version.get("messages", {}).get(message_name, {}).get("initial_data", {})
        )

    initial_data = dict(
        (k, pre_serialize_timedelta(v)) for k, v in initial_data.items()
    )

    return initial_data


def validate_workflow_spec(workflow_spec_config):

    serializer = WorkflowSpecConfigSerializer(data=workflow_spec_config)
    if serializer.is_valid():
        pass
    else:
        raise Exception(
            {
                "message": "settings WORKFLOW_SPEC_CONFIG not valid",
                "details": serializer.errors,
            }
        )
    return serializer.data

class WorkflowSpecConfigVerionListSerializer(serializers.DictField):
    def run_validation(self, data=empty):
        def validate_field(field):
            return bool(re.match(r"(\d+\.)+(\d+\.)+(\d+)", field))

        if data is not empty:
            not_valid = [f for f in set(data) if not validate_field(f)]
            if not_valid:
                raise serializers.ValidationError(
                    f"Versioning incorrect: {', '.join(not_valid)}"
                )

        return super().run_validation(data)

class WorkflowSpecConfigVerionSerializer(serializers.Serializer):
    messages = serializers.DictField(required=False, child=serializers.DictField())

class WorkflowSpecConfigThemeSerializer(serializers.Serializer):
    initial_data = serializers.DictField()
    versions = WorkflowSpecConfigVerionListSerializer(
        child=WorkflowSpecConfigVerionSerializer()
    )

    def run_validation(self, data=empty):
        if data is not empty:
            unknown = set(data) - set(self.fields)
            if unknown:
                errors = ["Unknown field: {}".format(f) for f in unknown]
                raise serializers.ValidationError(
                    {
                        "error": errors,
                    }
                )

        return super().run_validation(data)
class WorkflowSpecConfigThemeTypeSerializer(serializers.Serializer):
    visit = WorkflowSpecConfigThemeSerializer(required=False)
    vve = WorkflowSpecConfigThemeSerializer(required=False)
    def run_validation(self, data=empty):
        if data is not empty:
            unknown = set(data) - set(self.fields)
            if unknown:
                errors = ["Unknown field: {}".format(f) for f in unknown]
                raise serializers.ValidationError(
                    {
                        "error": errors,
                    }
                )

        return super().run_validation(data)
class WorkflowSpecConfigSerializer(serializers.Serializer):
    default = WorkflowSpecConfigThemeTypeSerializer()
    visit = WorkflowSpecConfigThemeSerializer(required=False)
    vve = WorkflowSpecConfigThemeSerializer(required=False)
    def run_validation(self, data=empty):
        if data is not empty:
            unknown = set(data) - set(self.fields)
            if unknown:
                errors = ["Unknown field: {}".format(f) for f in unknown]
                raise ValueError

        return super().run_validation(data)
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

    objects = BulkCreateSignalsManager()

    @property
    def get_form_variables(self):
        # TODO: Return corresponding spiff task data, currently used only to provide frontend with the current summon_id
        return self.workflow.get_data()

    def complete(self):
        self.completed = True
        self.save()
#TODO:  Move
def parse_task_spec_form(form):
    trans_types = {
        "enum": "select",
        "boolean": "checkbox",
        "string": "text",
        "long": "number",
    }
    fields = [
        {
            "label": f.label,
            "options": [
                {
                    "value": o.id,
                    "label": o.name,
                }
                for o in f.__dict__.get("options", [])
            ],
            "name": f.id,
            "type": "multiselect"
            if bool([v.name for v in f.validation if v.name == "multiple"])
            else trans_types.get(f.type, "text"),
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
