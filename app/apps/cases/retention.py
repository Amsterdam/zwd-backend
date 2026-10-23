from datetime import date
from django.db.models import Q
from django.utils import timezone

BEWAARTERMIJN_SUCCESVOL_JAREN = 5
BEWAARTERMIJN_AFGEBROKEN_JAREN = 1
# Closed cases without a CaseClose (e.g. legacy imports) get the longest period
BEWAARTERMIJN_ONBEKEND_JAREN = 5
RESULTAAT_ONBEKEND = "Onbekend"


def get_case_close(case):
    # A case has at most one CaseClose (see CaseCloseSerializer.validate_case).
    # Iterate over .all() so a prefetch_related("caseclose_set") is used.
    return next(iter(case.caseclose_set.all()), None)


def get_retention_years(case):
    """
    Returns the retention period in years based on the close reason,
    or None if the case is still open.
    """
    if not case.end_date:
        return None
    case_close = get_case_close(case)
    if not case_close:
        return BEWAARTERMIJN_ONBEKEND_JAREN
    if case_close.reason.is_successful:
        return BEWAARTERMIJN_SUCCESVOL_JAREN
    return BEWAARTERMIJN_AFGEBROKEN_JAREN


def get_retention_expiry_date(case):
    """
    The retention period starts on January 1st of the year after the end date,
    so it always expires on December 31st of end_date.year + retention years.
    """
    years = get_retention_years(case)
    if years is None:
        return None
    return date(case.end_date.year + years, 12, 31)


def get_result_label(case):
    """
    Returns the close reason, "Onbekend" for a closed case without a CaseClose,
    or an empty string if the case is still open.
    """
    if not case.end_date:
        return ""
    case_close = get_case_close(case)
    return case_close.reason.name if case_close else RESULTAAT_ONBEKEND


def retention_cutoff(years, reference_date=None):
    """
    Cases with an end_date before this date have an expired retention period,
    e.g. with 1 year on 2028-01-01 the cutoff is 2027-01-01, so a case closed
    on 2026-10-21 is expired from that day on.
    """
    reference_date = reference_date or timezone.localdate()
    return date(reference_date.year - years, 1, 1)


def _successful_expired_q(reference_date=None):
    return Q(
        caseclose__reason__is_successful=True,
        end_date__lt=retention_cutoff(BEWAARTERMIJN_SUCCESVOL_JAREN, reference_date),
    )


def _unsuccessful_expired_q(reference_date=None):
    return Q(
        caseclose__reason__is_successful=False,
        end_date__lt=retention_cutoff(BEWAARTERMIJN_AFGEBROKEN_JAREN, reference_date),
    )


def _unknown_expired_q(reference_date=None):
    return Q(
        caseclose__isnull=True,
        end_date__lt=retention_cutoff(BEWAARTERMIJN_ONBEKEND_JAREN, reference_date),
    )


def _closed_not_archived(queryset):
    return queryset.filter(end_date__isnull=False, archived_at__isnull=True)


def filter_successful_expired(queryset, reference_date=None):
    return _closed_not_archived(queryset).filter(_successful_expired_q(reference_date))


def filter_unsuccessful_expired(queryset, reference_date=None):
    return _closed_not_archived(queryset).filter(
        _unsuccessful_expired_q(reference_date)
    )


def filter_unknown_expired(queryset, reference_date=None):
    return _closed_not_archived(queryset).filter(_unknown_expired_q(reference_date))


def filter_retention_expired(queryset, reference_date=None):
    """Closed, not yet archived cases whose retention period has expired."""
    return _closed_not_archived(queryset).filter(
        _successful_expired_q(reference_date)
        | _unsuccessful_expired_q(reference_date)
        | _unknown_expired_q(reference_date)
    )


def filter_retention_running(queryset, reference_date=None):
    """Closed, not yet archived cases whose retention period is still running."""
    expired = filter_retention_expired(queryset, reference_date)
    return _closed_not_archived(queryset).exclude(pk__in=expired.values("pk"))
