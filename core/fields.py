"""
For custom field types -- Related to the Django ORM
"""

import struct

from django.db import models


class VersionNumber(object):

    @classmethod
    def string_to_version(cls, version_str):
        return VersionNumber(*version_str.split('.'))

    def __init__(self, major, minor=0, patch=0, build=0):
        self.number = (int(major), int(minor), int(patch), int(build))
        if any([i < 0 or i > 255 for i in self.number]):
            raise ValueError(
                "Version number components must between 0 and 255,"
                " inclusive")

    def __int__(self):
        """
        Maps a version number to a two's complement signed 32-bit integer by
        first calculating a signed 32-bit integer, then casts to signed by
        subtracting 2**31
        """
        major, minor, patch, build = self.number
        num = major << 24 | minor << 16 | patch << 8 | build
        return num - 2**31

    def __str__(self):
        """
        Pretty printing of version number; doesn't print 0's on the end
        """
        end_index = 0
        for index, part in enumerate(self.number):
            if part != 0:
                end_index = index

        return ".".join([str(i) for i in self.number[:end_index + 1]])

    def __repr__(self):
        return "<VersionNumber(%d, %d, %d, %d)>" % self.number


class VersionNumberField(models.Field):

    """
    A version number. Stored as a integer. Retrieved as a VersionNumber. Like
    magic. Major, minor, patch, build must not exceed 255
    """
    __metaclass__ = models.SubfieldBase

    def get_internal_type(self):
        return 'IntegerField'

    def to_python(self, value):
        """
        Convert a int to a VersionNumber
        """
        if value is None:
            return None
        if isinstance(value, VersionNumber):
            return value
        if isinstance(value, tuple):
            return VersionNumber(*value)
        if isinstance(value, str)\
                or isinstance(value, unicode):
            return VersionNumber.string_to_version(value)

        part_bytes = struct.pack(">I", value + 2**31)
        part_ints = [ord(i) for i in part_bytes]
        return VersionNumber(*part_ints)

    def get_prep_value(self, value):
        """
        Convert a VersionNumber or tuple to an int
        """
        if isinstance(value, tuple):
            value = VersionNumber(*value)
        if isinstance(value, int):
            return value

        return int(value)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        return self.get_prep_value(value)
