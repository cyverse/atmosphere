"""
  Instance model for atmosphere.
"""
from hashlib import md5
from datetime import datetime, timedelta

from django.db import (
    models, transaction, DatabaseError
)
from django.db.models import (
    Q, ObjectDoesNotExist
)
from django.utils import timezone

import pytz

from rtwo.models.instance import MockInstance
from rtwo.models.machine import MockMachine
from rtwo.models.size import MockSize
from rtwo.models.size import OSSize

from threepio import logger

from core.models.deploy_record import DeployRecord
from core.models.identity import Identity
from core.models.instance_source import InstanceSource
from core.models.machine import (
    convert_esh_machine, get_or_create_provider_machine
)
from core.models.volume import convert_esh_volume
from core.models.size import (
    convert_esh_size, Size
)
from core.models.tag import Tag
from core.models.managers import ActiveInstancesManager
from atmosphere import settings


class Instance(models.Model):
    """
    When a user launches a machine, an Instance is created.
    Instances are described by their Name and associated Tags
    Instances have a specific ID of the machine or volume
    they were created from (source)
    Instances have a specific ID provided by the cloud provider (provider_alias)
    The IP Address, creation and termination date,
    and the user who launched the instance are recorded for logging purposes.
    """
    esh = None
    name = models.CharField(max_length=256)
    project = models.ForeignKey("Project", null=True, blank=True, related_name='instances')
    # TODO: CreateUUIDfield that is *not* provider_alias?
    # token is used to help instance 'phone home' to server post-deployment.
    token = models.CharField(max_length=36, blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    # The specific machine & provider for which this instance exists
    source = models.ForeignKey(InstanceSource, related_name='instances')
    provider_alias = models.CharField(max_length=256, unique=True)
    ip_address = models.GenericIPAddressField(null=True, unpack_ipv4=True)
    created_by = models.ForeignKey('AtmosphereUser')
    #FIXME: Why is null=True okay here?
    created_by_identity = models.ForeignKey(Identity, null=True)
    shell = models.BooleanField(default=False)
    vnc = models.BooleanField(default=False)
    web_desktop = models.BooleanField(default=False)
    password = models.CharField(max_length=64, blank=True, null=True)
    # FIXME  Problems when setting a default, missing auto_now_add
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)

    # Model Managers
    objects = models.Manager()  # The default manager.
    active_instances = ActiveInstancesManager()

    @property
    def project_name(self):
        if not self.created_by_identity:
            return None
        return self.created_by_identity.get_credential('ex_project_name')

    @property
    def provider(self):
        return self.source.provider

    @property
    def project_owner(self):
        project = self.project
        if not project:
            return None
        return project.owner

    @staticmethod
    def shared_with_user(user, is_leader=None):
        """
        is_leader: Explicitly filter out instances if `is_leader` is True/False, if None(default) do not test for project leadership.
        """
        ownership_query = Q(created_by=user)
        project_query = Q(project__owner__memberships__user=user)
        if is_leader == False:
            project_query &= Q(project__owner__memberships__is_leader=False)
        elif is_leader == True:
            project_query &= Q(project__owner__memberships__is_leader=True)
        membership_query = Q(created_by__memberships__group__user=user)
        return Instance.objects.filter(membership_query | project_query | ownership_query).distinct()

    def get_total_hours(self):
        from service.monitoring import _get_allocation_result
        identity = self.created_by_identity
        limit_instances = [self.provider_alias]
        result = _get_allocation_result(
            identity,
            limit_instances=limit_instances)
        total_hours = result.total_runtime().total_seconds()/3600.0
        hours = round(total_hours, 2)
        return hours

    def get_first_history(self):
        """
        Returns the first InstanceStatusHistory
        """
        # TODO: Profile Option
        # except InstanceStatusHistory.DoesNotExist:
        # TODO: Profile current choice
        try:
            return self.instancestatushistory_set.order_by(
                'start_date').first()
        except ObjectDoesNotExist:
            return None

    def get_last_history(self):
        """
        Returns the latest InstanceStatusHistory if it exists
        """
        return self.instancestatushistory_set.order_by('start_date').last()

    def end_date_all(self, end_date=None):
        """
        Call this function to tie up loose ends when the instance is finished
        (Destroyed, terminated, no longer exists..)
        """
        if not end_date:
            end_date = timezone.now()
        deploy_records = self.deployrecord_set.filter(
            end_date=None).update(end_date=end_date, status=DeployRecord.CANCELLED)
        ish_list = self.instancestatushistory_set.filter(end_date=None).update(
                end_date=end_date)
        if not self.end_date:
            logger.info("END DATING instance %s: %s" % (self.provider_alias, end_date))
            self.end_date = end_date
            self.save()

    def creator_name(self):
        if not self.created_by:
            return "N/A"
        return self.created_by.username

    def hash_alias(self):
        return md5(self.provider_alias).hexdigest()

    def hash_machine_alias(self):
        if self.esh and self.esh._node\
           and self.esh._node.extra\
           and self.esh._node.extra.get('imageId'):
            return md5(self.esh._node.extra['imageId']).hexdigest()
        else:
            try:
                if self.source:
                    return md5(self.source.identifier).hexdigest()
            except InstanceSource.DoesNotExist:
                logger.exception(
                    "Unable to find provider_machine for %s." %
                    self.provider_alias)
        return 'Unknown'

    def esh_fault(self):
        if self.esh:
            return self.esh.extra.get('fault', {})
        return {}

    def get_status(self):
        last_history = self.get_last_history()
        return last_history and last_history.status.name

    def get_activity(self):
        last_history = self.get_last_history()
        return last_history and last_history.activity

    def get_provider(self):
        if not self.source:
            return
        return self.source.provider

    def get_size(self):
        history = self.get_last_history()
        return history and history.size

    def esh_size(self):
        if not self.esh or not hasattr(self.esh, 'extra'):
            last_history = self.get_last_history()
            if last_history:
                return last_history.size.alias
            return "Unknown"
        extras = self.esh.extra
        if 'flavorId' in extras:
            return extras['flavorId']
        elif 'instance_type' in extras:
            return extras['instance_type']
        elif 'instancetype' in extras:
            return extras['instancetype']
        else:
            return "Unknown"

    def application_uuid(self):
        if self.source.is_machine():
            return self.source.providermachine\
                    .application_version.application.uuid
        else:
            return None

    def application_name(self):
        if self.source.is_machine():
            return self.source.providermachine\
                    .application_version.application.name
        else:
            return None

    def application_id(self):
        if self.source.is_machine():
            return self.source.providermachine\
                    .application_version.application.id
        else:
            return None

    @property
    def volume(self):
        if self.source.is_volume():
            return self.source.volume
        return None

    @property
    def provider_machine(self):
        if self.source.is_machine():
            return self.source.providermachine
        return None

    def esh_source_name(self):
        if self.source.is_machine():
            return self.source.providermachine\
                    .application_version.application.name
        elif self.source.is_volume():
            return self.source.volume.name
        else:
            return "%s - Source Unknown" % self.source.identifier

    def provider_uuid(self):
        return self.source.provider.uuid

    def provider_name(self):
        return self.source.provider.location

    def esh_source(self):
        return self.source.identifier

    @property
    def allocation_source(self):
        # FIXME: look up the current allocation source by "Scanning the event table" on this instance.
        from core.models.allocation_source import InstanceAllocationSourceSnapshot as Snapshot
        snapshot = Snapshot.objects.filter(instance=self).first()
        return snapshot.allocation_source if snapshot else None

    def change_allocation_source(self, allocation_source, user=None):
        """
        Call this method when you want to issue a 'change_allocation_source' event to the database.
        """
        from core.models.event_table import EventTable
        if not user:
            user = self.created_by
        #FIXME: comment out this line for AllocationSource
        if not allocation_source:
            raise Exception("Allocation source must not be null")
        payload = {
                'allocation_source_name': allocation_source.name,
                'instance_id': self.provider_alias
        }
        return EventTable.create_event(
            "instance_allocation_source_changed",
            payload,
            user.username)

    def json(self):
        return {
            'alias': self.provider_alias,
            'name': self.name,
            'tags': [tag.json() for tag in self.tags.all()],
            'ip_address': self.ip_address,
            'provider_machine': self.provider_machine.json(),
            'created_by': self.created_by.username,
        }

    def __unicode__(self):
        return "%s (Name:%s, Creator:%s, IP:%s)" %\
            (self.provider_alias, self.name,
             self.creator_name(), self.ip_address)

    class Meta:
        db_table = "instance"
        app_label = "core"


"""
Useful utility methods for the Core Model..
"""

def strfdelta(tdelta, fmt=None):
    from string import Formatter
    if not fmt:
        # The standard, most human readable format.
        fmt = "{D} days {H:02} hours {M:02} minutes {S:02} seconds"
    if tdelta == timedelta():
        return "0 minutes"
    formatter = Formatter()
    return_map = {}
    div_by_map = {'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    keys = map(lambda x: x[1], list(formatter.parse(fmt)))
    remainder = int(tdelta.total_seconds())
    for unit in ('D', 'H', 'M', 'S'):
        if unit in keys and unit in div_by_map.keys():
            return_map[unit], remainder = divmod(remainder, div_by_map[unit])

    return formatter.format(fmt, **return_map)


def strfdate(datetime_o, fmt=None):
    if not fmt:
        # The standard, most human readable format.
        fmt = "%m/%d/%Y %H:%M:%S"
    if not datetime_o:
        datetime_o = timezone.now()
    return datetime_o.strftime(fmt)


def find_instance(instance_id):
    if type(instance_id) == int:
        core_instance = Instance.objects.filter(id=instance_id)
    else:
        core_instance = Instance.objects.filter(provider_alias=instance_id)
    if len(core_instance) > 1:
        logger.warn(
            "Multiple instances returned for instance_id - %s" %
            instance_id)
    if core_instance:
        return core_instance[0]
    return None


def _find_esh_ip(esh_instance):
    if esh_instance.ip:
        return esh_instance.ip

    ip_address = "0.0.0.0"
    try:
        ips = esh_instance.extra["addresses"].values()
        ip_address = [ip for ip in ips[0]
                      if ip["OS-EXT-IPS:type"] == "floating"][0]["addr"]
    except Exception:
        pass
    return ip_address


def _update_core_instance(core_instance, ip_address, password):
    core_instance.ip_address = ip_address
    if password:
        core_instance.password = password
    if core_instance.end_date:
        logger.warn("ERROR - Instance %s prematurley 'end-dated'."
                    % core_instance.provider_alias)
        core_instance.end_date = None
    core_instance.save()


def _find_esh_start_date(esh_instance):
    if 'launchdatetime' in esh_instance.extra:
        create_stamp = esh_instance.extra.get('launchdatetime')
    elif 'launch_time' in esh_instance.extra:
        create_stamp = esh_instance.extra.get('launch_time')
    elif 'created' in esh_instance.extra:
        create_stamp = esh_instance.extra.get('created')
    else:
        raise Exception(
            "Instance does not have a created timestamp.  This"
            "should never happen. Don't cheat and assume it was created just "
            "now. Get the real launch time, bra.")
    start_date = _convert_timestamp(create_stamp)
    logger.debug("Launched At: %s" % create_stamp)
    logger.debug("Started At: %s" % start_date)
    return start_date


def _convert_timestamp(iso_8601_stamp):
    if not iso_8601_stamp:
        return None

    try:
        datetime_obj = datetime.strptime(
            iso_8601_stamp,
            '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        try:
            datetime_obj = datetime.strptime(
                iso_8601_stamp,
                '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            raise ValueError(
                "Expected ISO8601 Timestamp in Format: "
                "YYYY-MM-DDTHH:MM:SS[.ssss][Z]")
    # All Dates are UTC relative
    datetime_obj = datetime_obj.replace(tzinfo=pytz.utc)
    return datetime_obj


def convert_instance_source(
        esh_driver,
        esh_instance,
        esh_source,
        provider_uuid,
        identity_uuid,
        user):
    """
    Given the instance source, create the appropriate core REPR and return
    """
    from rtwo.models.volume import BaseVolume
    from rtwo.models.machine import BaseMachine
    # TODO: Future Release..
    new_source = None
    if isinstance(esh_source, BaseVolume):
        core_source = convert_esh_volume(
            esh_source,
            provider_uuid,
            identity_uuid,
            user)
    elif isinstance(esh_source, BaseMachine):
        if isinstance(esh_source, MockMachine):
            # MockMachine includes only the Alias/ID information
            # so a lookup on the machine is required to get accurate
            # information.
            new_source = esh_driver.get_machine(esh_source.id)
        if not new_source:
            core_source = get_or_create_provider_machine(
                esh_source.id,
                "Inactive Machine for Instance %s" %
                esh_instance.id,
                provider_uuid)
        else:
            core_source = convert_esh_machine(esh_driver, new_source,
                                              provider_uuid, user)
    elif not isinstance(esh_source, BaseMachine):
        raise Exception("Encountered unknown source %s" % esh_source)
    return core_source


def convert_esh_instance(
        esh_driver,
        esh_instance,
        provider_uuid,
        identity_uuid,
        user,
        token=None,
        password=None):
    from core.models import InstanceStatusHistory
    instance_id = esh_instance.id
    ip_address = _find_esh_ip(esh_instance)
    source_obj = esh_instance.source
    core_instance = find_instance(instance_id)
    if core_instance:
        _update_core_instance(core_instance, ip_address, password)
    else:
        start_date = _find_esh_start_date(esh_instance)
        core_source = convert_instance_source(
            esh_driver,
            esh_instance,
            source_obj,
            provider_uuid,
            identity_uuid,
            user)
        core_instance = create_instance(
            provider_uuid,
            identity_uuid,
            instance_id,
            core_source.instance_source,
            ip_address,
            esh_instance.name,
            user,
            start_date,
            token,
            password)
    core_instance.esh = esh_instance
    status = esh_instance.extra.get('status')

    # Cannot rely on dict.get(field, default) since attributes 'task' and
    # 'fault' exist but are None
    activity = esh_instance.extra.get('task') or ''
    fault = esh_instance.extra.get('fault') or ''

    # Atmosphere creates its own states like "networking" and "deploying",
    # that are sub-states of Openstack's "active" state. We exit here if we
    # detect we are in said sub-state, to prevent overriding it with "active".
    last_history = core_instance.get_last_history()
    if status == "active" and not activity and (last_history and last_history.is_atmo_specific()):
        return

    import ipdb; ipdb.set_trace()
    core_size = convert_esh_size(esh_instance.size, provider_uuid)
    InstanceStatusHistory.update_history(
        core_instance,
        status,
        activity,
        size=core_size,
        extra=fault)
    return core_instance


def set_instance_from_metadata(esh_driver, core_instance):
    """
    NOT BEING USED ANYMORE.. DEPRECATED..
    """
    # Fixes Dep. loop - Do not remove
    from api.serializers import InstanceSerializer
    # Breakout for drivers (Eucalyptus) that don't support metadata
    if not hasattr(esh_driver._connection, 'ex_get_metadata'):
        # logger.debug("EshDriver %s does not have function 'ex_get_metadata'"
        #            % esh_driver._connection.__class__)
        return core_instance
    try:
        esh_instance = esh_driver.get_instance(core_instance.provider_alias)
        if not esh_instance:
            return core_instance
        metadata = esh_driver._connection.ex_get_metadata(esh_instance)
    except Exception:
        logger.exception("Exception retrieving instance metadata for %s" %
                         core_instance.provider_alias)
        return core_instance

    # TODO: Match with actual instance launch metadata in service/instance.py
    # TODO: Probably best to redefine serializer as InstanceMetadataSerializer
    # TODO: Define a creator and their identity by the METADATA instead of
    # assuming its the person who 'found' the instance

    serializer = InstanceSerializer(core_instance, data=metadata,
                                    partial=True)
    if not serializer.is_valid():
        logger.warn("Encountered errors serializing metadata:%s"
                    % serializer.errors)
        return core_instance
    core_instance = serializer.save()
    core_instance.esh = esh_instance
    return core_instance


def create_instance(
        provider_uuid,
        identity_uuid,
        provider_alias,
        instance_source,
        ip_address,
        name,
        creator,
        create_stamp,
        token=None,
        password=None):
    # TODO: Define a creator and their identity by the METADATA instead of
    # assuming its the person who 'found' the instance
    identity = Identity.objects.get(uuid=identity_uuid)
    new_inst = Instance.objects.create(name=name,
                                       provider_alias=provider_alias,
                                       source=instance_source,
                                       ip_address=ip_address,
                                       created_by=creator,
                                       created_by_identity=identity,
                                       token=token,
                                       password=password,
                                       shell=False,
                                       start_date=create_stamp)
    new_inst.save()
    if token:
        logger.debug("New instance created - %s<%s> (Token = %s)" %
                     (name, provider_alias, token))
    else:
        logger.debug("New instance object - %s<%s>" %
                     (name, provider_alias,))
    # FIXME: create instance_status_history here, pass in size & status to help
    return new_inst
