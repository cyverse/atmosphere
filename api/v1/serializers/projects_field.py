from django.contrib.auth.models import AnonymousUser
from core.models.group import get_user_group
from core.models.project import Project
from rest_framework import serializers


class ProjectsField(serializers.Field):

    def to_representation(self, project_mgr):
        request_user = self.parent.request_user
        if isinstance(request_user, AnonymousUser):
            return None
        try:
            group = get_user_group(request_user.username)
            projects = project_mgr.filter(owner=group)
            # Modifications to how 'project' should be displayed here:
            return [p.uuid for p in projects]
        except Project.DoesNotExist:
            return None

    def to_internal_value(self, data, files, field_name, into):
        value = data.get(field_name)
        if value is None:
            return
        related_obj = self.parent.instance
        user = self.parent.request_user
        group = get_user_group(user.username)
        # Retrieve the New Project(s)
        if isinstance(value, list):
            project_id = value[0]
        else:
            project_id = value

        new_project = Project.objects.get(id=project_id, owner=group)
        related_obj.project = new_project
        related_obj.save()
        # Modifications to how 'project' should be displayed here:
        into[field_name] = project_id
