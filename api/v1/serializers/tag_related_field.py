from core.models.identity import Identity
from core.models.tag import find_or_create_tag
from rest_framework import serializers


class TagRelatedField(serializers.SlugRelatedField):

    def to_native(self, tag):
        return super(TagRelatedField, self).to_native(tag)

    def field_from_native(self, data, files, field_name, into):
        value = data.get(field_name)
        if value is None:
            return
        try:
            tags = []
            for tagname in value:
                tag = find_or_create_tag(tagname, None)
                tags.append(tag)
            into[field_name] = tags
        except Identity.DoesNotExist:
            into[field_name] = None
        return
