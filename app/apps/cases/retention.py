from datetime import date

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
