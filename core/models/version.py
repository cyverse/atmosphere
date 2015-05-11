"""
  ApplicationVersion models for atmosphere.
"""
import uuid

from django.db import models
from django.utils import timezone
from threepio import logger

from core.models.license import License
from core.models.identity import Identity
from core.models.tag import Tag

from atmosphere import settings

class ApplicationVersion(models.Model):
    """
    As an Application is Updated/Forked, it may be replicated
    across server different providermachines/volumes.
    When creating the request the author will usually
    create/change 'common information'
    Things like:
      - Description
      - Installed Software
      - Excluded Files
    This is a container for that information.

    NOTE: Using this as the 'model' for DB moving to ID==UUID format.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey("Application", related_name="versions")
    fork_version = models.ForeignKey("ApplicationVersion", blank=True, null=True)
    name = models.CharField(max_length=32, blank=True, null=True)#Potentially goes unused..
    description = models.TextField(null=True, blank=True)
    #TODO: Dynamic location for upload_to
    icon = models.ImageField(upload_to="application_versions", null=True, blank=True)
    allow_imaging = models.BooleanField(default=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    #TODO: Decide if we want to enable this information.. Is it useful?
    #As it stands now, we collect this information on the request, but 
    # this would allow users to edit/interact/view?
    iplant_system_files = models.TextField(default='', null=True, blank=True)
    installed_software = models.TextField(default='', null=True, blank=True)
    excluded_files = models.TextField(default='', null=True, blank=True)
    licenses = models.ManyToManyField(License,
            blank=True, related_name='application_versions')
    membership = models.ManyToManyField('Group',
                                        related_name='application_versions',
                                        through='ApplicationVersionMembership',
                                        blank=True)
    def __unicode__(self):
        return "%s - %s" % (self.application.name, self.start_date)

    @property
    def str_id(self):
        return str(self.id)

    @property
    def icon_url(self):
        return self.icon.url if self.icon else None

class ApplicationVersionMembership(models.Model):
    """
    Members of a specific ApplicationVersion
    Members can view & launch respective machines.
    If the can_share flag is set, then members also have ownership--they can give
    membership to other users.
    The unique_together field ensures just one of those states is true.
    NOTE: There IS underlying cloud implementation 9/10 times. That should be 'hooked' in here!
    """
    application_version = models.ForeignKey(ApplicationVersion)
    group = models.ForeignKey('Group')
    can_share = models.BooleanField(default=False)

    def __unicode__(self):
        return "(ApplicationVersion:%s - Member:%s) " %\
            (self.application_version, self.group.name)

    class Meta:
        db_table = 'application_version_membership'
        app_label = 'core'
        unique_together = ('application_version', 'group')


def get_version_for_machine(provider_uuid, identifier):
    try:
        return ApplicationVersion.objects.filter(
            machines__instance_source__provider__uuid=provider_uuid,
            machines__instance_source__identifier=identifier)
    except ApplicationVersion.DoesNotExist:
        return None


def get_app_version(app, version):
    try:
        app_version = ApplicationVersion.objects.get(
            name=version,
            application=app)
        return app_version
    except ApplicationVersion.DoesNotExist:
        app_version = create_app_version(app)
        return app_version

def create_app_version(app, version="1.0"):
    app_version = ApplicationVersion.objects.create(
        application=app,
        name=version)
    last_version = app.latest_version
    if last_version:
        #DEFAULT: Inherit your information from your parents
        app_version.description=last_version.description
        app_version.icon=last_version.icon
        app_version.allow_imaging=last_version.allow_imaging
        app_version.save()
        transfer_licenses(last_version, app_version)
        transfer_membership(last_version, app_version)
    else:
        app_version.description = "New Application %s - Version %s" % (app.name, app_version.name)
        app_version.save()
    return app_version

def transfer_licenses(parent_version, new_version):
    if parent_version.licenses.count():
        for license in parent_version.licenses.all():
            new_version.licenses.add(license)

def transfer_membership(parent_version, new_version):
    if parent_version.membership.count():
        for member in parent_version.membership.all():
            #member == Group
            old_membership = ApplicationVersionMembership.objects.get(
                group=member, application_version=parent_version)
            membership, _ = ApplicationVersionMembership.objects.get_or_create(
                application_version = new_version,
                group = old_membership.group,
                can_share = old_membership.can_share)


