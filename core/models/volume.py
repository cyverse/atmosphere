from datetime import datetime
import pytz

from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models.provider import Provider
from core.models.identity import Identity
from threepio import logger


class Volume(models.Model):
    """
    """
    # esh field is filled out when converting an esh_volume
    esh = None
    alias = models.CharField(max_length=256)
    provider = models.ForeignKey(Provider)
    size = models.IntegerField()
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('AtmosphereUser', null=True)
    created_by_identity = models.ForeignKey(Identity, null=True)
    start_date = models.DateTimeField(default=lambda: datetime.now(pytz.utc))
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "volume"
        app_label = "core"

    def update(self, *args, **kwargs):
        """
        Allows for partial updating of the model
        """
        #Upload args into kwargs
        for arg in args:
            for (key, value) in arg.items():
                kwargs[key] = value
        #Update the values
        for key in kwargs.keys():
            if hasattr(self, key):
                try:
                    if key in ["provider"]:
                        continue
                    setattr(self, key, kwargs[key])
                except Exception:
                    logger.exception("Unable to update key: " + str(key))
        self.save()
        return self

    def get_projects(self, user):
        projects = self.projects.filter(
                Q(end_date=None) | Q(end_date__gt=timezone.now()),
                owner=user,
                )
        return projects

    def __unicode__(self):
        return "%s" % (self.alias,)

    def esh_status(self):
        if not self.esh or not self.esh.extra:
            return "Unknown"
        return self.esh.extra.get('status', 'Unknown')

    def esh_attach_data(self):
        if not self.esh or not self.esh.extra:
            return "Unknown"
        attach_data = self.esh.extra.get('attachmentSet', {})
        #Convert OpenStack attach_data to Euca-based
        if type(attach_data) is list and attach_data:
            attach_data = attach_data[0]

        if 'serverId' in attach_data:
            attach_data['instanceId'] = attach_data['serverId']
        return attach_data


def convert_esh_volume(esh_volume, provider_id, identity_id, user):
    """
    Get or create the core representation of esh_volume
    Attach esh_volume to the object for further introspection..
    """
    alias = esh_volume.id
    name = esh_volume.name
    size = esh_volume.size
    created_on = esh_volume.extra.get('createTime')
    try:
        volume = Volume.objects.get(alias=alias, provider__id=provider_id)
    except Volume.DoesNotExist:
        volume = create_volume(name, alias, size, provider_id, identity_id,
                               user, created_on)
    _check_project(volume, user)
    volume.esh = esh_volume
    return volume

def _check_project(core_volume, user):
    """
    Select a/multiple projects the volume belongs to.
    NOTE: User (NOT Identity!!) Specific
    """
    core_projects = core_volume.get_projects(user)
    if not core_projects:
        default_proj = user.get_default_project()
        default_proj.volumes.add(core_volume)
        core_projects = [default_proj]
    return core_projects

def create_volume(name, alias, size, provider_id, identity_id,
                  creator, created_on=None):
    provider = Provider.objects.get(id=provider_id)
    identity = Identity.objects.get(id=identity_id)
    volume = Volume.objects.create(name=name, alias=alias,
                                   size=size, provider=provider,
                                   created_by=creator,
                                   created_by_identity=identity,
                                   description='')
    if created_on:
        # Taking advantage of the ability to save string dates as datetime
        # but we need to get the actual date time after we are done..
        #NOTE: Why is this different than the method in convert_esh_instance
        #NOTE: -Steve
        volume.start_date = pytz.utc.localize(created_on)
        volume.save()
    volume = Volume.objects.get(id=volume.id)
    return volume
