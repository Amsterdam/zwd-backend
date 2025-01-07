import copy
from apps.workflow.models import CaseUserTask, CaseWorkflow
from .user_tasks import get_task_by_name


def complete_generic_user_task_and_create_new_user_tasks(case_user_task):
    task = CaseUserTask.objects.filter(id=case_user_task.case_user_task_id).first()
    if task:
        data = copy.deepcopy(case_user_task.variables)
        data.pop("mapped_form_data")
        user_task_type = get_task_by_name(task.task_name)
        user_task_instance = user_task_type(task)
        data.update(user_task_instance.get_data())
        CaseWorkflow.complete_user_task(task.id, data, wait=True)
