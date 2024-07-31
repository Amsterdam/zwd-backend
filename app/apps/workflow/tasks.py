import copy
from time import sleep

import celery
from apps.cases.models import Case
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.db import transaction

logger = get_task_logger(__name__)

DEFAULT_RETRY_DELAY = 2
MAX_RETRIES = 6

class BaseTaskWithRetry(celery.Task):
    autoretry_for = (Exception,)
    max_retries = MAX_RETRIES
    default_retry_delay = DEFAULT_RETRY_DELAY




@celery.shared_task(bind=True, base=BaseTaskWithRetry)
def task_accept_message_for_workflow(self, workflow_id, message, extra_data):
    from apps.workflow.models import CaseWorkflow

    workflow_instance = CaseWorkflow.objects.get(id=workflow_id)
    if workflow_instance.get_lock():
        with transaction.atomic():
            workflow_instance.accept_message(message, extra_data)
            return f"task_accept_message_for_workflow: message '{message}' for workflow with id {workflow_id}, accepted"

    raise Exception(
        f"task_accept_message_for_workflow: message '{message}' for workflow with id '{workflow_id}'', is busy"
    )


@celery.shared_task(bind=True, base=BaseTaskWithRetry)
def task_start_subworkflow(self, subworkflow_name, parent_workflow_id, extra_data={}):
    from apps.workflow.models import CaseWorkflow

    parent_workflow = CaseWorkflow.objects.get(id=parent_workflow_id)
    with transaction.atomic():
        data = copy.deepcopy(parent_workflow.get_data())
        data.update(extra_data)
        subworkflow = CaseWorkflow.objects.create(
            case=parent_workflow.case,
            parent_workflow=parent_workflow,
            workflow_type=subworkflow_name,
            data=data,
        )

    return f"task_start_subworkflow:  subworkflow id '{subworkflow.id}', for parent workflow with id '{parent_workflow_id}', created"


@celery.shared_task(bind=True, base=BaseTaskWithRetry)
def task_create_main_worflow_for_case(self, case_id, data={}):
    from apps.workflow.models import CaseWorkflow

    case = Case.objects.get(id=case_id)
    with transaction.atomic():
        workflow_instance = CaseWorkflow.objects.create(
            case=case,
            # TODO: Make dynamic
            workflow_type="process_vve_ok",
            main_workflow=True,
            workflow_message_name="main_process",
            data=data,
        )

    return f"task_start_main_worflow_for_case: workflow id '{workflow_instance.id}', for case with id '{case_id}', created"


@celery.shared_task(bind=True, base=BaseTaskWithRetry)
def task_start_worflow(self, worklow_id):
    from apps.workflow.models import CaseWorkflow
    workflow_instance = CaseWorkflow.objects.get(id=worklow_id)
    workflow_instance.start()

@celery.shared_task(bind=True, base=BaseTaskWithRetry)
def task_script_wait(self, workflow_id, message, extra_data={}):
    from apps.workflow.models import CaseWorkflow

    workflow_instance = CaseWorkflow.objects.get(id=workflow_id)

    if hasattr(workflow_instance.__class__, f"handle_{message}") and callable(
        getattr(workflow_instance.__class__, f"handle_{message}")
    ):
        data = getattr(workflow_instance, f"handle_{message}")(extra_data)

        if data:
            task_accept_message_for_workflow.delay(workflow_instance.id, message, data)

    return f"task_script_wait: message '{message}' for workflow with id '{workflow_id}', completed"



@celery.shared_task(bind=True, base=BaseTaskWithRetry)
def task_complete_user_task_and_create_new_user_tasks(self, task_id, data={}):
    from apps.workflow.models import CaseUserTask
    task = CaseUserTask.objects.get(id=task_id, completed=False)
    task.workflow.complete_user_task_and_create_new_user_tasks(task.task_id, data)
    return f"task_complete_user_task_and_create_new_user_tasks: complete task with name '{task.task_name}' for workflow with id '{task.workflow.id}', is completed"
