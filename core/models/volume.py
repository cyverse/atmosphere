from datetime import datetime
import pytz

from django.db import models
from django.utils import timezone

from core.models.provider import Provider
from threepio import logger


class Volume(models.Model):
    """
    """
    # esh field is filled out when converting an eshVolume
    esh = None
    alias = models.CharField(max_length=256)
    provider = models.ForeignKey(Provider)
    size = models.IntegerField()
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField(default=lambda:datetime.now(pytz.utc))
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

    def esh_status(self):
        if not self.esh or not self.esh.extra:
            return "Unknown"
        return self.esh.extra.get('status', 'Unknown')

    def esh_attach_data(self):
        if not self.esh or not self.esh.extra:
            return "Unknown"
        attach_data = self.esh.extra.get('attachmentSet', {})
        #Convert OpenStack attach_data to Euca-based
        if type(attach_data) is list:
            attach_data = attach_data[0]

        if 'serverId' in attach_data:
            attach_data['instanceId'] = attach_data['serverId']
        return attach_data


def convertEshVolume(eshVolume, provider_id, user):
    """
    Get or create the core representation of eshVolume
    Attach eshVolume to the object for further introspection..
    """
    alias = eshVolume.id
    name = eshVolume.name
    size = eshVolume.size
    created = eshVolume.extra.get('createTime')
    try:
        volume = Volume.objects.get(alias=alias, provider__id=provider_id)
    except Volume.DoesNotExist:
        volume = createVolume(name, alias, size, provider_id, created)
    volume.esh = eshVolume
    return volume


#TODO:Belongs in core.volume
def createVolume(name, alias, size, provider_id, created=None):
    provider = Provider.objects.get(id=provider_id)
    volume = Volume.objects.create(name=name, alias=alias,
                                   size=size, provider=provider,
                                   description='')
    if created:
    # Taking advantage of the ability to save string dates as datetime
    # but we need to get the actual date time after we are done..
        volume.start_date = pytz.utc.localize(created)
        volume.save()
    volume = Volume.objects.get(id=volume.id)
    return volume
