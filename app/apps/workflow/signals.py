import copy

from apps.workflow.models import CaseUserTask, CaseWorkflow, GenericCompletedTask
from apps.workflow.tasks import task_start_worflow
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .utils import get_latest_version_from_config
from .user_tasks import get_task_by_name


@receiver(
    post_save,
    sender=GenericCompletedTask,
    dispatch_uid="complete_generic_user_task_and_create_new_user_tasks",
)
def complete_generic_user_task_and_create_new_user_tasks(
    sender, instance, created, **kwargs
):
    task = CaseUserTask.objects.filter(id=instance.case_user_task_id).first()
    if created and task:
        data = copy.deepcopy(instance.variables)
        data.pop("mapped_form_data")
        user_task_type = get_task_by_name(task.task_name)
        user_task_instance = user_task_type(task)
        data.update(user_task_instance.get_data())
        CaseWorkflow.complete_user_task(task.id, data, wait=True)


@receiver(pre_save, sender=CaseWorkflow, dispatch_uid="case_workflow_pre_save")
def case_workflow_pre_save(sender, instance, **kwargs):
    if not instance.id:
        instance.data = instance.data if isinstance(instance.data, dict) else {}
        instance.data.update(
            {
                "advice_type": {"value": instance.case.advice_type},
                "hoa_is_small": {"value": instance.case.homeowner_association.is_small},
                "build_year": {"value": instance.case.homeowner_association.build_year},
                "has_major_shareholder": {
                    "value": instance.case.homeowner_association.has_major_shareholder
                },
            }
        )
        instance.workflow_version = get_latest_version_from_config(
            instance.workflow_type
        )


@receiver(post_save, sender=CaseWorkflow, dispatch_uid="start_workflow")
def start_workflow(sender, instance, created, **kwargs):
    if created:
        task_start_worflow.delay(instance.id)
