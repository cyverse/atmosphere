from core.models.application import ApplicationBookmark
from rest_framework import serializers


class ApplicationBookmarkSerializer(serializers.ModelSerializer):
    """
    """
    #TODO:Need to validate provider/identity membership on id change
    type = serializers.SerializerMethodField('get_bookmark_type')
    alias = serializers.SerializerMethodField('get_bookmark_alias')

    def get_bookmark_type(self, bookmark_obj):
        return "Application"

    def get_bookmark_alias(self, bookmark_obj):
        return bookmark_obj.application.uuid

    class Meta:
        model = ApplicationBookmark
        fields = ('type', 'alias')