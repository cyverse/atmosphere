"""
  Post Boot script model for atmosphere.
"""
import time
from hashlib import md5
import pytz

from django.db import models
from django.db.models import Q
from django.utils import timezone

from threepio import logger
from uuid import uuid4
from core.models.instance import Instance
from core.models.application import Application

class ScriptType(models.Model):
    """
    ScriptType objects are created by developers,
    they should NOT be added/removed unless there
    are corresponding logic-choices in core code.
    """
    name = models.CharField(max_length=128)
    description = models.TextField(null=True, blank=True)
    class Meta:
        db_table = 'script_type'
        app_label = 'core'
    def __unicode__(self):
        return self.name

class BootScript(models.Model):
    """
    BootScripts can be created as an isolated unit, before they are associated
    with a specific application or instance.
    """
    title = models.CharField(max_length=128)
    created_by = models.ForeignKey("AtmosphereUser")
    script_type = models.ForeignKey(ScriptType)
    script_text = models.TextField()
    #If True: run on resume, start, restart, and Initial Launch
    #If False: run on Initial Launch ONLY
    run_every_deploy = models.BooleanField(default=False)

    applications = models.ManyToManyField(Application, related_name='scripts')
    instances = models.ManyToManyField(Instance, related_name='scripts')

    class Meta:
        db_table = 'boot_script'
        app_label = 'core'
#Useful
def get_scripts_for_user(username):
    return BootScript.objects.filter(
            created_by__username=username)
def get_scripts_for_application(application_uuid):
    return BootScript.objects.filter(
            applications__uuid=application_uuid)
def get_scripts_for_instance(instance_id):
    return BootScript.objects.filter(
            instances__provider_alias=instance_id)
