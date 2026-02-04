from apps.cases.models import Case
from apps.workflow.models import (
    CaseWorkflow,
    CaseWorkflowStateHistory,
    GenericCompletedTask,
)
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .utils import get_latest_version_from_config
from django.utils import timezone
from django.db import transaction
from django.db.models import Prefetch
from apps.homeownerassociation.utils import hoa_with_counts


@receiver(pre_save, sender=CaseWorkflow, dispatch_uid="case_workflow_pre_save")
def case_workflow_pre_save(sender, instance, **kwargs):
    if not instance.id:
        instance.data = instance.data if isinstance(instance.data, dict) else {}
        case = Case.objects.prefetch_related(
            Prefetch("homeowner_association", queryset=hoa_with_counts())
        ).get(pk=instance.case_id)

        hoa = case.homeowner_association
        instance.data.update(
            {
                "application_type": {"value": instance.case.application_type},
                "advice_type": {"value": instance.case.advice_type},
                "hoa_is_small": {"value": hoa.is_small},
                "build_year": {"value": hoa.build_year},
                "has_major_shareholder": {"value": hoa.has_major_shareholder},
                "is_priority_neighborhood": {"value": hoa.is_priority_neighborhood},
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


@receiver(pre_save, sender=CaseWorkflow)
def snapshot_case_workflow_state(sender, instance: CaseWorkflow, **kwargs):
    if not instance.pk or instance.completed:
        return

    previous = (
        sender.objects.filter(pk=instance.pk)
        .only("serialized_workflow_state", "data")
        .first()
    )

    if not previous.serialized_workflow_state:
        return

    if previous.serialized_workflow_state == instance.serialized_workflow_state:
        return

    CaseWorkflowStateHistory.objects.create(
        workflow=instance,
        serialized_workflow_state=previous.serialized_workflow_state,
        data=previous.data,
    )


@receiver(
    post_save,
    sender=CaseWorkflow,
)
def delete_case_workflow_state_history(sender, instance, created, **kwargs):
    if created:
        return

    if not instance.completed:
        return

    history_qs = CaseWorkflowStateHistory.objects.filter(workflow=instance)

    if not history_qs.exists():
        return

    history_qs.delete()


# Updated Case.updated field if task is completed / generic task is created
@receiver(
    post_save,
    sender=GenericCompletedTask,
    dispatch_uid="update_case_updated_timestamp_on_task_complete",
)
def update_case_updated_timestamp_on_task_complete(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(
            lambda: Case.objects.filter(id=instance.case_id).update(
                updated=timezone.now()
            )
        )
