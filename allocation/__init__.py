"""
"""


def validate_interval(start_date, end_date, raise_exception=True):
    """
    Returns whether the interval is valid.
    #NOTE: Should this also test if start_date <= end_date? -SG

    If raise_exception=True then validate_interval will `raise`
    an exception if the interval is invalid.

    Otherwise, validate_interval will return False
    """
    if start_date and not start_date.tzinfo:
        if raise_exception:
            raise Exception("Invalid Start Date: %s Reason: Missing Timezone.")
        else:
            return False

    if end_date and not end_date.tzinfo:
        if raise_exception:
            raise Exception("Invalid End Date: %s Reason: Missing Timezone.")
        else:
            return False

    return True
