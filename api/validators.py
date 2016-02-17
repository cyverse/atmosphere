"""
Custom validators for Django-rest-framework Fields go here:
"""
from rest_framework import serializers

# This is an example of a Function-based validator


def no_special_characters(value):
    invalid_chars = '!"#$%&\'*+,/;<=>?@[\\]^`{|}~'
    # Noteably ABSENT (These are "OKAY"): ()-.
    if any(char in invalid_chars for char in value):
        raise serializers.ValidationError(
            "The value '%s' contains one or more "
            "special characters that are invalid." % value)


# This is an example of a Class-based validator


class NoSpecialCharacters(object):
    def __init__(self, character_set):
        self.invalid_chars = character_set

    def __call__(self, value):
        if any(char in self.invalid_chars for char in value):
            message = "The value '%s' contains one or more " \
                      "special characters that are invalid." % value
            raise serializers.ValidationError(message)
