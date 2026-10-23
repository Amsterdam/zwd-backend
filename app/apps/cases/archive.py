import logging
from dataclasses import dataclass, field
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from apps.cases.models import Case, CaseDocument
from apps.events.models import CaseEvent
from apps.homeownerassociation.models import Contact
from apps.workflow.models import CaseUserTask, CaseWorkflow, GenericCompletedTask
from .retention import filter_retention_expired

logger = logging.getLogger(__name__)


@dataclass
class ArchivePlan:
    """
    Describes what archiving a selection of cases will do. It is used both for
    the dry-run (confirmation page) and for the actual archiving, so both
    always work on the same set of cases and homeowner associations.
    """

    case_ids: list = field(default_factory=list)
    skipped_not_expired_ids: list = field(default_factory=list)
    skipped_open_ids: list = field(default_factory=list)
    skipped_archived_ids: list = field(default_factory=list)
    # Homeowner associations whose contacts are deleted, because all of their
    # other cases are archived (or will be archived by this plan)
    hoa_ids_delete_contacts: list = field(default_factory=list)
    # Homeowner associations whose contacts are kept, because they still have
    # a case that is not archived
    hoa_ids_keep_contacts: list = field(default_factory=list)

    @property
    def skipped_count(self):
        return (
            len(self.skipped_not_expired_ids)
            + len(self.skipped_open_ids)
            + len(self.skipped_archived_ids)
        )

    def counts(self):
        """Number of objects that will be deleted when this plan is executed."""
        return {
            "workflows": CaseWorkflow.objects.filter(case_id__in=self.case_ids).count(),
            "tasks": CaseUserTask.objects.filter(case_id__in=self.case_ids).count(),
            "documents": CaseDocument.objects.filter(case_id__in=self.case_ids).count(),
            "completed_tasks": GenericCompletedTask.objects.filter(
                case_id__in=self.case_ids
            ).count(),
            "events": CaseEvent.objects.filter(case_id__in=self.case_ids).count(),
            "contacts": Contact.objects.filter(
                homeowner_association_id__in=self.hoa_ids_delete_contacts
            ).count(),
        }


def build_archive_plan(queryset, reference_date=None):
    """
    Determines which cases in the queryset can be archived (retention period
    expired) and which homeowner associations lose their contacts.
    """
    plan = ArchivePlan()
    expired_ids = set(
        filter_retention_expired(queryset, reference_date).values_list("pk", flat=True)
    )

    for pk, end_date, archived_at in queryset.order_by("pk").values_list(
        "pk", "end_date", "archived_at"
    ):
        if pk in expired_ids:
            plan.case_ids.append(pk)
        elif archived_at:
            plan.skipped_archived_ids.append(pk)
        elif not end_date:
            plan.skipped_open_ids.append(pk)
        else:
            plan.skipped_not_expired_ids.append(pk)

    hoa_ids = set(
        Case.objects.filter(
            pk__in=plan.case_ids, homeowner_association__isnull=False
        ).values_list("homeowner_association_id", flat=True)
    )
    hoa_ids_with_other_cases = set(
        Case.objects.filter(
            homeowner_association_id__in=hoa_ids, archived_at__isnull=True
        )
        .exclude(pk__in=plan.case_ids)
        .values_list("homeowner_association_id", flat=True)
    )
    plan.hoa_ids_delete_contacts = sorted(hoa_ids - hoa_ids_with_other_cases)
    plan.hoa_ids_keep_contacts = sorted(hoa_ids_with_other_cases)
    return plan


def _delete_files(names):
    for name in names:
        try:
            default_storage.delete(name)
        except Exception:
            logger.exception(f"Could not delete archived case document {name}")


def archive_case(case_id):
    """
    Deletes workflows, tasks, documents, task history and timeline of a case.
    The case itself, its CaseClose and ActivationTeam are kept.
    """
    with transaction.atomic():
        CaseWorkflow.objects.filter(case_id=case_id).delete()
        CaseUserTask.objects.filter(case_id=case_id).delete()

        documents = CaseDocument.objects.filter(case_id=case_id)
        document_names = list(documents.values_list("document", flat=True))
        documents.delete()
        # Only remove the files once the database changes are committed
        transaction.on_commit(lambda: _delete_files(document_names))

        GenericCompletedTask.objects.filter(case_id=case_id).delete()
        CaseEvent.objects.filter(case_id=case_id).delete()

        # update() instead of save(): Case.save() would emit a new CaseEvent
        Case.objects.filter(pk=case_id).update(archived_at=timezone.now())


def delete_hoa_contacts(hoa_ids):
    """
    Deletes the contacts of the given homeowner associations, but only if all
    of their cases are archived. Returns the number of deleted contacts.
    """
    hoa_ids_with_unarchived_cases = Case.objects.filter(
        homeowner_association_id__in=hoa_ids, archived_at__isnull=True
    ).values("homeowner_association_id")
    deleted, _ = (
        Contact.objects.filter(homeowner_association_id__in=hoa_ids)
        .exclude(homeowner_association_id__in=hoa_ids_with_unarchived_cases)
        .delete()
    )
    return deleted


def execute_archive_plan(plan):
    """
    Archives all cases in the plan, then deletes the contacts of homeowner
    associations without unarchived cases. Each case is archived in its own
    transaction, so a failure halfway keeps the cases archived so far and the
    action can simply be run again.
    """
    counts = plan.counts()
    for case_id in plan.case_ids:
        archive_case(case_id)
    counts["contacts"] = delete_hoa_contacts(plan.hoa_ids_delete_contacts)
    logger.info(f"Archived cases {plan.case_ids}, deleted: {counts}")
    return counts
