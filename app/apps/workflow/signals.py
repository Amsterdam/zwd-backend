from apps.cases.models import Case
from apps.workflow.models import CaseWorkflow, GenericCompletedTask
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .utils import get_latest_version_from_config
from django.utils import timezone


@receiver(pre_save, sender=CaseWorkflow, dispatch_uid="case_workflow_pre_save")
def case_workflow_pre_save(sender, instance, **kwargs):
    if not instance.id:
        instance.data = instance.data if isinstance(instance.data, dict) else {}
        instance.data.update(
            {
                "application_type": {"value": instance.case.application_type},
                "advice_type": {"value": instance.case.advice_type},
                "hoa_is_small": {"value": instance.case.homeowner_association.is_small},
                "build_year": {"value": instance.case.homeowner_association.build_year},
                "has_major_shareholder": {
                    "value": instance.case.homeowner_association.has_major_shareholder
                },
                "is_priority_neighborhood": {
                    "value": instance.case.homeowner_association.is_priority_neighborhood
                },
            }
        )
        existing_main_workflow = CaseWorkflow.objects.filter(
            case=instance.case,
            main_workflow=True,
        ).first()
        instance.workflow_version = get_latest_version_from_config(
            instance.workflow_type,
            existing_main_workflow.workflow_version if existing_main_workflow else None,
        )


# Updated Case.updated field if task is completed / generic task is created
@receiver(
    post_save,
    sender=GenericCompletedTask,
    dispatch_uid="update_case_updated_timestamp_on_task_complete",
)
def update_case_updated_timestamp_on_task_complete(sender, instance, created, **kwargs):
    Case.objects.filter(id=instance.case_id).update(updated=timezone.now())
