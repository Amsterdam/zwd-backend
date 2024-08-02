from apps.cases.models import Case
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=Case, dispatch_uid="start_workflow_for_case")
def start_workflow_for_case(sender, instance, created, **kwargs):
    from apps.workflow.tasks import task_create_main_worflow_for_case

    if kwargs.get("raw"):
        return
    data = {}
    if created:
        task_create_main_worflow_for_case.delay(case_id=instance.id, data=data)
