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

from rtwo.models.machine import MockMachine
from rtwo.models.size import MockSize

from threepio import logger

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

    @classmethod
    def for_user(self, user):
        identity_ids = user.current_identities.values_list('id', flat=True)
        qs = Instance.objects.filter(created_by_identity__in=identity_ids)
        return qs

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

    def get_projects(self, user):
        # TODO: Replace with 'only_current'
        projects = self.projects.filter(
            Q(end_date=None) | Q(end_date__gt=timezone.now()),
            owner=user,
        )
        return projects

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
        Returns the newest InstanceStatusHistory
        """
        # FIXME: Clean up this implementation OR rename to `get_or_create`
        # TODO: Profile Option
        # except InstanceStatusHistory.DoesNotExist:
        # TODO: Profile current choice
	#FIXME: Move this call so that it happens inside InstanceStatusHistory to avoid circ.dep.
        last_history = self.instancestatushistory_set.order_by(
            '-start_date').first()
        if last_history:
            return last_history
        else:
            unknown_size, _ = Size.objects.get_or_create(
                name='Unknown Size', alias='N/A', provider=self.provider,
                cpu=-1, mem=-1, root=-1, disk=-1)
            last_history = self._build_first_history(
                'Unknown', unknown_size, self.start_date, self.end_date, True)
            logger.warn("No history existed for %s until now. "
                        "An 'Unknown' history was created" % self)
            return last_history

    def _build_first_history(self, status_name, size,
                             start_date, end_date=None, first_update=False, activity=None):
	#FIXME: Move this call so that it happens inside InstanceStatusHistory to avoid circ.dep.
        from core.models import InstanceStatusHistory
        if not first_update and status_name not in [
                'build',
                'pending',
                'running']:
            logger.info("First Update Unknown - Status name on instance \
                        %s: %s - %s"
                        % (self.provider_alias, status_name))
            # Instance state is 'unknown' from start of instance until now
            # NOTE: This is needed to prevent over-charging accounts
            status_name = 'unknown'
            activity = None
        first_history = InstanceStatusHistory.create_history(
            status_name, self, size, start_date=start_date, end_date=end_date, activity=activity)
        first_history.save()
        return first_history

    def update_history(
            self,
            status_name,
            size,
            task=None,
            tmp_status=None,
            first_update=False):
        """
        Given the status name and size, look up the previous history object
        If nothing has changed: return (False, last_history)
        else: end date previous history object, start new history object.
              return (True, new_history)
        """
	#FIXME: Move this call so that it happens inside InstanceStatusHistory to avoid circ.dep.
        from core.models import InstanceStatusHistory
        import traceback
        # 1. Get status name
        status_name = _get_status_name_for_provider(
            self.provider_machine.provider,
            status_name,
            task,
            tmp_status)
        activity = self.esh_activity()
        # 2. Get the last history (or Build a new one if no other exists)
        last_history = self.get_last_history()
        if not last_history:
            last_history = InstanceStatusHistory.create_history(
                status_name, self, size, start_date=self.start_date, activity=activity)
            last_history.save()
            logger.debug("STATUSUPDATE - FIRST - Instance:%s Old Status: %s - %s New\
                Status: %s Tmp Status: %s" % (self.provider_alias,
                                              self.esh_status(),
                                              self.esh_activity(),
                                              status_name,
                                              tmp_status))
            logger.debug("STATUSUPDATE - Traceback: %s"
                         % traceback.format_stack())
        # 2. Size and name must match to continue using last history
        if last_history.status.name == status_name \
                and last_history.size.id == size.id:
            # logger.info("status_name matches last history:%s " %
            #        last_history.status.name)
            return (False, last_history)
        logger.debug("STATUSUPDATE - Instance:%s Old Status: %s - %s New Status: %s\
            Tmp Status: %s" % (self.provider_alias,
                               self.esh_status(),
                               self.esh_activity(),
                               status_name,
                               tmp_status))
        logger.debug("STATUSUPDATE - Traceback: %s" % traceback.format_stack())
        # 3. ASSERT: A new history item is required due to a State or Size
        # Change
        now_time = timezone.now()
        try:
            new_history = InstanceStatusHistory.transaction(
                status_name, activity, self, size,
                start_time=now_time,
                last_history=last_history)
            return (True, new_history)
        except ValueError:
            logger.exception("Bad transaction")
            return (False, last_history)

    def _calculate_active_time(self, delta=None):
        if not delta:
            # Default delta == Time since instance created.
            delta = timezone.now() - self.start_date

        past_time = timezone.now() - delta
        recent_history = self.instancestatushistory_set.filter(
            Q(end_date=None) | Q(end_date__gt=past_time)
        ).order_by('start_date')
        total_time = timedelta()
        inst_prefix = "HISTORY,%s,%s" % (self.created_by.username,
                                         self.provider_alias[:5])
        for idx, state in enumerate(recent_history):
            # Can't start counting any earlier than 'delta'
            if state.start_date < past_time:
                start_count = past_time
            else:
                start_count = state.start_date
            # If date is current, stop counting 'right now'
            if not state.end_date:
                final_count = timezone.now()
            else:
                final_count = state.end_date

            if state.is_active():
                # Active time is easy
                active_time = final_count - start_count
            else:
                # Inactive states are NOT counted against the user
                active_time = timedelta()
            # multiply by CPU count of size.
            cpu_time = active_time * state.size.cpu
            logger.debug("%s,%s,%s,%s CPU,%s,%s,%s,%s"
                         % (inst_prefix, state.status.name,
                            state.size.name, state.size.cpu,
                            strfdate(start_count), strfdate(final_count),
                            strfdelta(active_time), strfdelta(cpu_time)))
            total_time += cpu_time
        return total_time

    def get_active_hours(self, delta):
        # Don't move it up. Circular reference.
        from service.monitoring import delta_to_hours
        total_time = self._calculate_active_time(delta)
        return delta_to_hours(total_time)

    def get_active_time(self, earliest_time=None, latest_time=None):
        """
        Return active time, and the reference list that was counted.
        """
        accounting_list = self._accounting_list(earliest_time, latest_time)

        total_time = timedelta()
        for state in accounting_list:
            total_time += state.cpu_time
        return total_time, accounting_list

    def recent_history(self, earliest_time, latest_time):
        """
        Return all Instance Status History
          Currently Running
          OR
          Terminated after: now() - delta (ex:7 days, 1 month, etc.)
        """
        active_history = self.instancestatushistory_set.filter(
            # Collect history that is Current or has 'countable' time..
            Q(end_date=None) | Q(end_date__gt=earliest_time)
        ).order_by('start_date')
        return active_history

    def _accounting_list(self, earliest_time=None, latest_time=None):
        """
        Return the list of InstanceStatusHistory that should be counted,
        according to the limits of 'earliest_time' and 'latest_time'
        """
        if not latest_time:
            latest_time = timezone.now()
        # Determine the earliest time to start counts.
        if not earliest_time:
            earliest_time = self.start_date

        accounting_list = []
        active_history = self.recent_history(earliest_time, latest_time)

        for state in active_history:
            (active_time, start_count, end_count) = state.get_active_time(
                earliest_time, latest_time)
            state.active_time = active_time
            state.start_count = start_count
            state.end_count = end_count
            state.cpu_time = active_time * state.size.cpu
            accounting_list.append(state)
        return accounting_list

    def end_date_all(self, end_date=None):
        """
        Call this function to tie up loose ends when the instance is finished
        (Destroyed, terminated, no longer exists..)
        """
        if not end_date:
            end_date = timezone.now()
        ish_list = self.instancestatushistory_set.filter(end_date=None)
        for ish in ish_list:
            # logger.info('Saving history:%s' % ish)
            if not ish.end_date:
                logger.info("END DATING instance history %s: %s" % (ish, end_date))
                ish.end_date = end_date
                ish.save()
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

    def esh_status(self):
        if self.esh:
            return self.esh.get_status()
        last_history = self.get_last_history()
        if last_history:
            return last_history.status.name
        else:
            return "Unknown"

    def esh_activity(self):
        activity = None
        if self.esh:
            try:
                activity = " ".join(self.esh.get_status().split(' - ')[1:]).strip()
            except:
                activity = None
            return activity
        last_history = self.get_last_history()
        if last_history:
            try:
                activity = " ".join(last_history.status.split(' - ')[1:]).strip()
            except:
                activity = None
            return activity
        else:
            return "Unknown"

    def get_size(self):
        return self.get_last_history().size

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
        #FIXME: look up the current allocation source by "Scanning the event table" on this instance.
        from core.models.allocation_source import \
                InstanceAllocationSourceSnapshot as Snapshot
        snapshot = Snapshot.objects.filter(instance=self).first()
        return snapshot.allocation_source if snapshot else None

    def change_allocation_source(self, allocation_source, user=None):
        """
        Call this method when you want to issue a 'change_allocation_source' event to the database.
        """
        if not settings.USE_ALLOCATION_SOURCE:
            return
        from core.models.event_table import EventTable
        if not user:
            user = self.created_by
        #FIXME: comment out this line for AllocationSource
        if not allocation_source:
            raise Exception("Allocation source must not be null")
        payload = {
                'allocation_source_id': allocation_source.source_id,
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
OPENSTACK_TASK_STATUS_MAP = {
    # Terminate tasks
    # Suspend tasks
    'resuming': 'build',
    'suspending': 'suspended',
    # Shutdown tasks
    'powering-on': 'build',
    'shutting-down': 'suspended',
    # Instance launch tasks
    'initializing': 'build',
    'scheduling': 'build',
    'spawning': 'build',
    # Atmosphere Task-specific lines
    'networking': 'networking',
    'deploying': 'deploying',
    'running_boot_script': 'deploying',
    'deploy_error': 'deploy_error',
    'boot_script_error': 'deploy_error',
}
OPENSTACK_ACTIVE_STATES = ['active']
OPENSTACK_INACTIVE_STATES = ['build', 'suspended', 'shutoff', 'Unknown']


def _get_status_name_for_provider(
        provider,
        status_name,
        task_name=None,
        tmp_status=None):
    """
    Purpose: to be used in lookups/saves
    Return the appropriate InstanceStatus
    """
    provider_type = provider.get_type_name().lower()
    if provider_type == 'openstack':
        return _get_openstack_name_map(status_name, task_name, tmp_status)
    logger.warn(
        "Could not find a strategy for provider type:%s" %
        provider_type)
    return status_name


def _get_openstack_name_map(status_name, task_name, tmp_status):
    new_status = None
    if task_name:
        new_status = OPENSTACK_TASK_STATUS_MAP.get(task_name)

    if new_status:
        logger.debug("Task provided:%s, Status maps to %s"
                     % (task_name, new_status))
    elif tmp_status:
        # ASSERT: task_name = None
        if 'running_boot_script' in tmp_status:
            tmp_status = 'running_boot_script' # Avoid problems due to keeping track of scripts executed 1/2, 2/3, etc.
        new_status = OPENSTACK_TASK_STATUS_MAP.get(tmp_status)
        logger.debug(
            "Tmp_status provided:%s, Status maps to %s" %
            (tmp_status, new_status))
    if not new_status:
        # ASSERT: tmp_status = None
        return status_name
    # ASSERT: new_status exists.
    # Determine precedence/override based on status_name.
    if status_name in OPENSTACK_ACTIVE_STATES:
        return new_status
    else:
        # This covers cases like 'shutoff - deploy_error' being marked as
        # 'shutoff'
        return status_name


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
    try:
        if not hasattr(esh_instance, "extra")\
           or not esh_instance.extra.get("addresses"):
            return "0.0.0.0"
        ips = esh_instance.extra["addresses"].values()
        ip_address = [ip for ip in ips[0]
                      if ip["OS-EXT-IPS:type"] == "floating"][0]["addr"]
    except Exception:  # no public ip
        try:
            ip_address = [ip for ip in ips[0]
                          if ip["OS-EXT-IPS:type"] == "fixed"][0]["addr"]
        except Exception:  # no private ip
            ip_address = "0.0.0.0"
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
    """
    """
    instance_id = esh_instance.id
    ip_address = _find_esh_ip(esh_instance)
    source_obj = esh_instance.source
    core_instance = find_instance(instance_id)
    if core_instance:
        _update_core_instance(core_instance, ip_address, password)
    else:
        start_date = _find_esh_start_date(esh_instance)
        logger.debug("Instance: %s" % instance_id)
        core_source = convert_instance_source(
            esh_driver,
            esh_instance,
            source_obj,
            provider_uuid,
            identity_uuid,
            user)
        logger.debug("CoreSource: %s" % core_source)
        # Use New/Existing core Machine to create core Instance
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
    # Add 'esh' object
    core_instance.esh = esh_instance
    # Update the InstanceStatusHistory
    core_size = _esh_instance_size_to_core(esh_driver,
                                           esh_instance, provider_uuid)
    # TODO: You are the mole!
    core_instance.update_history(
        esh_instance.extra['status'],
        core_size,
        esh_instance.extra.get('task'),
        esh_instance.extra.get('metadata', {}).get('tmp_status', "MISSING"))

    # Update values in core with those found in metadata.
    # core_instance = set_instance_from_metadata(esh_driver, core_instance)
    return core_instance


def _esh_instance_size_to_core(esh_driver, esh_instance, provider_uuid):
    # NOTE: Querying for esh_size because esh_instance
    # Only holds the alias, not all the values.
    # As a bonus this is a cached-call
    esh_size = esh_instance.size
    if isinstance(esh_size, MockSize):
        # MockSize includes only the Alias/ID information
        # so a lookup on the size is required to get accurate
        # information.
        # TODO: Switch to 'get_cached_size!'
        new_size = esh_driver.get_size(esh_size.id)
        if new_size:
            esh_size = new_size
    core_size = convert_esh_size(esh_size, provider_uuid)
    return core_size


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
    # NOTE: No instance_status_history here, because status is not passed
    return new_inst
