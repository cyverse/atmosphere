from datetime import datetime
import pytz

from django.db import models, transaction, DatabaseError
from django.db.models import Q
from django.utils import timezone

from core.models.abstract import InstanceSource
from core.models.provider import Provider
from core.models.identity import Identity
from threepio import logger


class Volume(InstanceSource):
    size = models.IntegerField()
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True, null=True)
    def source_start_date(self):
        return self.instancesource_ptr.start_date
    def source_end_date(self):
        return self.instancesource_ptr.end_date
    def source_provider(self):
        return self.instancesource_ptr.provider
    def source_identifier(self):
        return self.instancesource_ptr.identifier

    class Meta:
        db_table = "volume"
        app_label = "core"



    def end_date_all(self):
        if not self.end_date:
            self.end_date = timezone.datetime.now()
            self.save()


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
            owner=user)
        return projects

    def __unicode__(self):
        return "%s" % (self.source_identifier(),)

    def get_status(self):
        if self.esh and self.esh.extra:
            status = self.esh.extra["status"]
            tmp_status = self.esh.extra.get('tmp_status','')
            if tmp_status:
                return "%s - %s" % (status, tmp_status)
            return status
        last_history = self._get_last_history()
        if last_history:
            return last_history.status.name
        else:
            return VolumeStatus.UNKNOWN

    def get_device(self):
        attach_data = self.get_attach_data()
        if attach_data and attach_data.get("device"):
            return attach_data["device"]

    def get_instance_alias(self):
        attach_data = self.get_attach_data()
        if attach_data and attach_data.get("instance_alias"):
            return attach_data["instance_alias"]

    def get_attach_data(self):
        if self.esh and self.esh.extra:
            attach_data = self.esh.extra.get('attachments', {})
        else:
            attach_data = {}
        if attach_data:
            if type(attach_data) is list and attach_data:
                attach_data = attach_data[0]
            if "serverId" in attach_data:
                attach_data["instance_alias"] = attach_data["serverId"]
            return attach_data
        else:
            last_history = self._get_last_history()
            if last_history\
               and (last_history.status.name == VolumeStatus.INUSE\
                    or last_history.status.name == VolumeStatus.ATTACHING):
                return last_history.get_attach_data()
        return None

    def mount_location(self):
        """
        TODO: Refactor and use get_metadata.
        """
        metadata = {}
        if self.esh and self.esh.extra:
            metadata = self.esh.extra.get('metadata', {})
        return metadata.get('mount_location',None)

    def esh_attach_data(self):
        """
        TODO: Refactor and use get_attach_data.
        """
        return self.get_attach_data()

    def esh_status(self):
        """
        TODO: Refactor and use get_status.
        """
        return self.get_status()

    def _get_last_history(self):
        last_history = self.volumestatushistory_set.all()\
                                                   .order_by('-start_date')
        if not last_history:
            return None
        return last_history[0]

    def _should_update(self, last_history):
        """
        Returns whether a new VolumeStatusHistory needs to be created.
        """
        return not last_history\
            or self.get_status() != last_history.status.name\
            or self.get_device() != last_history.device\
            or self.get_instance_alias() != last_history.instance_alias

    def _update_history(self):
        status = self.get_status()
        device = self.get_device()
        instance_alias = self.get_instance_alias()
        if status != VolumeStatus.UNKNOWN:
            last_history = self._get_last_history()
            if self._should_update(last_history):
                with transaction.atomic():
                    try:
                        new_history = VolumeStatusHistory.factory(self)
                        if last_history:
                            last_history.end_date = new_history.start_date
                            last_history.save()
                        new_history.save()
                    except DatabaseError as dbe:
                        logger.exception("volume_status_history: Lock is already acquired by"
                                         "another transaction.")


def convert_esh_volume(esh_volume, provider_uuid, identity_uuid, user):
    """
    Get or create the core representation of esh_volume
    Attach esh_volume to the object for further introspection..
    """
    identifier = esh_volume.id
    name = esh_volume.name
    size = esh_volume.size
    created_on = esh_volume.extra.get('createTime')
    try:
        volume = Volume.objects.get(identifier=identifier, provider__uuid=provider_uuid)
    except Volume.DoesNotExist:
        volume = create_volume(name, identifier, size, provider_uuid, identity_uuid,
                               user, created_on)
    volume.esh = esh_volume
    volume._update_history()
    return volume


def create_volume(name, identifier, size, provider_uuid, identity_uuid,
                  creator, description=None, created_on=None):
    provider = Provider.objects.get(uuid=provider_uuid)
    identity = Identity.objects.get(uuid=identity_uuid)
    volume = Volume.objects.create(
            name=name, description=description, size=size,
            identifier=identifier, provider=provider,
            created_by=creator, created_by_identity=identity)
            
    if created_on:
        # Taking advantage of the ability to save string dates as datetime
        # but we need to get the actual date time after we are done..
        #NOTE: Why is this different than the method in convert_esh_instance
        #NOTE: -Steve
        volume.start_date = pytz.utc.localize(created_on)
        volume.save()
    volume = Volume.objects.get(id=volume.id)
    return volume


class VolumeStatus(models.Model):
    """
    Used to enumerate the types of actions
    (I.e. available, in-use, attaching, detaching)
    """
    name = models.CharField(max_length=128)

    UNKNOWN = "Unknown"
    INUSE = "in-use"
    ATTACHING = "attaching"
    DETACHING = "detaching"

    def __unicode__(self):
        return "%s" % self.name

    class Meta:
        db_table = "volume_status"
        app_label = "core"


class VolumeStatusHistory(models.Model):
    """
    Used to keep track of each change in volume status.
    """
    volume = models.ForeignKey(Volume)
    status = models.ForeignKey(VolumeStatus)
    device = models.CharField(max_length=128, null=True, blank=True)
    instance_alias = models.CharField(max_length=36, null=True, blank=True)
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

    @classmethod
    def factory(cls, volume, start_date=None):
        """
        Creates a new VolumeStatusHistory.

        NOTE: Unsaved!
        """
        status, _ = VolumeStatus.objects.get_or_create(
            name=volume.get_status())
        device = volume.get_device()
        instance_alias = volume.get_instance_alias()
        new_history = VolumeStatusHistory(
            volume=volume,
            device=device,
            instance_alias=instance_alias,
            status=status)
        if start_date:
            new_history.start_date = start_date
        logger.debug("Created new history object: %s " % (new_history))
        return new_history

    def get_attach_data(self):
        """
        Get attach_data from this VolumeStatusHistory.
        """
        return {"device": self.device,
                "id": self.volume.source_identifier(),
                "instance_alias": self.instance_alias}

    class Meta:
        db_table = "volume_status_history"
        app_label = "core"
