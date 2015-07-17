"""
  ApplicationVersion models for atmosphere.
"""
import uuid

from django.db import models, IntegrityError
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
    # Required
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey("Application", related_name="versions")
    # NOTE: Parent is 'null' when this version was created by a STAFF user
    # (import, etc.)
    parent = models.ForeignKey("ApplicationVersion", blank=True, null=True)
    name = models.CharField(max_length=256)  # Potentially goes unused..
    # Optional/default available
    change_log = models.TextField(null=True, blank=True)
    allow_imaging = models.BooleanField(default=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    # User/Identity that created the version object
    created_by = models.ForeignKey('AtmosphereUser')
    created_by_identity = models.ForeignKey(Identity, null=True)
    # TODO: Decide if we want to enable this information.. Is it useful?
    # As it stands now, we collect this information on the request, but
    # this would allow users to edit/interact/view?
    iplant_system_files = models.TextField(default='', null=True, blank=True)
    installed_software = models.TextField(default='', null=True, blank=True)
    excluded_files = models.TextField(default='', null=True, blank=True)
    licenses = models.ManyToManyField(
        License,
        blank=True,
        related_name='application_versions')
    membership = models.ManyToManyField('Group',
                                        related_name='application_versions',
                                        through='ApplicationVersionMembership',
                                        blank=True)

    class Meta:
        db_table = 'application_version'
        app_label = 'core'
        unique_together = ('application', 'name')

    # NOTE: Created_by, created_by_ident will be == Application (EVERY TIME!)
    def __unicode__(self):
        return "%s:%s - %s" % (self.application.name,
                               self.name,
                               self.start_date)

    @property
    def machine_ids(self):
        return self.machines.values_list(
            'instance_source__identifier',
            flat=True)

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


def get_app_version(app, version, created_by=None, created_by_identity=None):
    try:
        app_version = ApplicationVersion.objects.get(
            name=version,
            application=app)
        return app_version
    except ApplicationVersion.DoesNotExist:
        app_version = create_app_version(
            app,
            version,
            created_by,
            created_by_identity)
        return app_version


def create_unique_version(app, version, created_by, created_by_identity):
    while True:
        try:
            app_version = ApplicationVersion.objects.create(
                application=app,
                name=version,
                created_by=created_by,
                created_by_identity=created_by_identity,
            )
            return app_version
        except IntegrityError as duplicate_found:
            logger.warn(
                "Version %s is taken for Application %s" %
                (version, app))
            version += ".0"


def create_app_version(
        app,
        version_str,
        created_by=None,
        created_by_identity=None):
    if not created_by:
        created_by = app.created_by
    if not created_by_identity:
        created_by_identity = app.created_by_identity
    app_version = create_unique_version(
        app,
        version_str,
        created_by,
        created_by_identity)
    last_version = app.latest_version
    if last_version:
        # DEFAULT: Inherit your information from your parents
        app_version.change_log = last_version.change_log
        app_version.allow_imaging = last_version.allow_imaging
        app_version.save()
        transfer_licenses(last_version, app_version)
        transfer_membership(last_version, app_version)
    else:
        app_version.change_log = "New Application %s - Version %s" % (
            app.name, app_version.name)
        app_version.save()
    return app_version


def transfer_licenses(parent_version, new_version):
    if parent_version.licenses.count():
        for license in parent_version.licenses.all():
            new_version.licenses.add(license)


def transfer_membership(parent_version, new_version):
    if parent_version.membership.count():
        for member in parent_version.membership.all():
            old_membership = ApplicationVersionMembership.objects.get(
                group=member, application_version=parent_version)
            membership, _ = ApplicationVersionMembership.objects.get_or_create(
                application_version=new_version,
                group=old_membership.group,
                can_share=old_membership.can_share)
