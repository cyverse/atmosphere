"""
For custom field types -- Related to the Django ORM
"""


class VersionNumber(object):
    @classmethod
    def string_to_version(cls, version_str):
        return VersionNumber(*version_str.split('.'))

    def __init__(self, major, minor=0, patch=0, build=0):
        self.number = (int(major), int(minor), int(patch), int(build))
        if any([i < 0 or i > 255 for i in self.number]):
            raise ValueError(
                "Version number components must between 0 and 255,"
                " inclusive"
            )

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
