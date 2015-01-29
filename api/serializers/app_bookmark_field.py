from django.contrib.auth.models import AnonymousUser
from core.models.application import ApplicationBookmark
from rest_framework import serializers


class AppBookmarkField(serializers.WritableField):

    def to_native(self, bookmark_mgr):
        request_user = self.root.request_user
        if type(request_user) == AnonymousUser:
            return False
        try:
            bookmark_mgr.get(user=request_user)
            return True
        except ApplicationBookmark.DoesNotExist:
            return False

    def field_from_native(self, data, files, field_name, into):
        value = data.get(field_name)
        if value is None:
            return
        app = self.root.object
        user = self.root.request_user
        if value:
            ApplicationBookmark.objects.\
                get_or_create(application=app, user=user)
            result = True
        else:
            ApplicationBookmark.objects\
                               .filter(application=app, user=user).delete()
            result = False
        into[field_name] = result