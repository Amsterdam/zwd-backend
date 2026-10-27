from django.db import migrations
from django.db.models import OuterRef, Subquery

# Task id of "Toekennen aan adviseur" in all versions of facturatie.bpmn
ADVISOR_TASK_NAME = "Activity_0rqmvm4"


def backfill_advisor_assigned_at(apps, schema_editor):
    """
    Uses the completion date of the most recent "Toekennen aan adviseur" task.
    Cases without such a task (e.g. legacy imports) keep an empty date.
    """
    Case = apps.get_model("cases", "Case")
    GenericCompletedTask = apps.get_model("workflow", "GenericCompletedTask")

    latest_task_date = (
        GenericCompletedTask.objects.filter(
            case_id=OuterRef("pk"), task_name=ADVISOR_TASK_NAME
        )
        .order_by("-date_added")
        .values("date_added")[:1]
    )
    Case.objects.filter(advisor__isnull=False, advisor_assigned_at__isnull=True).update(
        advisor_assigned_at=Subquery(latest_task_date)
    )


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0030_case_advisor_assigned_at"),
        ("workflow", "0013_alter_caseworkflowstatehistory_options"),
    ]

    operations = [
        migrations.RunPython(backfill_advisor_assigned_at, migrations.RunPython.noop),
    ]
