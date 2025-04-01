from apps.workflow.models import CaseWorkflow
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .utils import get_latest_version_from_config


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
                "is_priority_neighborhood": {
                    "value": instance.case.homeowner_association.is_priority_neighborhood
                },
            }
        )
        # existing_main_workflow = CaseWorkflow.objects.filter(
        #     case=instance.case,
        #     main_workflow=True,
        # ).first()
        instance.workflow_version = get_latest_version_from_config(
            instance.workflow_type
        )
