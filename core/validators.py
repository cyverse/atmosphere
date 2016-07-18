import pytz
from django.core.exceptions import ValidationError


def validate_timezone(value):
    if value not in pytz.all_timezones:
        raise ValidationError(
            "%s is not a timezone name" % value
        )
