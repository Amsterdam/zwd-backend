
from apps.workflow.models import  CaseWorkflow
from apps.workflow.tasks import task_start_worflow

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=CaseWorkflow, dispatch_uid="start_workflow")
def start_workflow(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    if created:
        task_start_worflow(instance.id)