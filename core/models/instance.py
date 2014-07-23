"""
  Instance model for atmosphere.
"""
import time
from hashlib import md5
from datetime import datetime, timedelta

from django.db import models, transaction, DatabaseError
from django.db.models import Q
from django.utils import timezone

import pytz

from rtwo.machine import MockMachine
from rtwo.size import MockSize

from threepio import logger

from core.models.identity import Identity
from core.models.machine import ProviderMachine, convert_esh_machine
from core.models.size import convert_esh_size
from core.models.tag import Tag

def strfdelta(tdelta, fmt=None):
    from string import Formatter
    if not fmt:
        #The standard, most human readable format.
        fmt = "{D} days {H:02} hours {M:02} minutes {S:02} seconds"
    if tdelta == timedelta():
        return "0 minutes"
    formatter = Formatter()
    return_map = {}
    div_by_map = {'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    keys = map( lambda x: x[1], list(formatter.parse(fmt)))
    remainder = int(tdelta.total_seconds())

    for unit in ('D', 'H', 'M', 'S'):
        if unit in keys and unit in div_by_map.keys():
            return_map[unit], remainder = divmod(remainder, div_by_map[unit])

    return formatter.format(fmt, **return_map)

def strfdate(datetime_o, fmt=None):
    if not fmt:
        #The standard, most human readable format.
        fmt = "%m/%d/%Y %H:%M:%S"
    if not datetime_o:
        datetime_o = timezone.now()
    return datetime_o.strftime(fmt)

class Instance(models.Model):
    """
    When a user launches a machine, an Instance is created.
    Instances are described by their Name and associated Tags
    Instances have a specific ID
    of the machine they were created from (Provider Machine)
    Instances have a specific ID of their own (Provider Alias)
    The IP Address, creation and termination date,
    and the user who launched the instance are recorded for logging purposes.
    """
    esh = None
    name = models.CharField(max_length=256)
    #TODO: Create custom Uuidfield?
    #token = Used for looking up the instance on deployment
    token = models.CharField(max_length=36, blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True)
    # The specific machine & provider for which this instance exists
    provider_machine = models.ForeignKey(ProviderMachine)
    provider_alias = models.CharField(max_length=256, unique=True)
    ip_address = models.GenericIPAddressField(null=True, unpack_ipv4=True)
    created_by = models.ForeignKey('AtmosphereUser')
    created_by_identity = models.ForeignKey(Identity, null=True)
    shell = models.BooleanField(default=False)
    vnc = models.BooleanField(default=False)
    password = models.CharField(max_length=64, blank=True, null=True)
    start_date = models.DateTimeField() # Problems when setting a default.
    end_date = models.DateTimeField(null=True)

    def get_projects(self, user):
        projects = self.projects.filter(
                Q(end_date=None) | Q(end_date__gt=timezone.now()),
                owner=user,
                )
        return projects

    def get_last_history(self):
        """
        Returns the newest InstanceStatusHistory
        """
        #TODO: Profile Option
        #try:
        #    return self.instancestatushistory_set.latest('id')
        #except InstanceStatusHistory.DoesNotExist:
        #    return None
            
        #TODO: Profile current choice
        last_history = self.instancestatushistory_set.all().order_by('-start_date')
        if not last_history:
            return None
        return last_history[0]

    def _build_first_history(self, status_name, size, start_date,
                             first_update=False):
        if not first_update and status_name not in ['build', 'pending', 'running']:
            #Instance state is 'unknown' from start of instance until now
            #NOTE: This is needed to prevent over-charging accounts
            status_name = 'unknown'
        first_history = InstanceStatusHistory.create_history(
                status_name, size, start_date)
        first_history.save()
        return first_history

    def _task_to_status(self, task_name):
        task_status_map = {
                #Suspend tasks
                'resuming':'build',
                'suspending':'suspended',
                #Shutdown tasks
                'powering-on':'active',
                'powering-off':'suspended',
                #Instance launch tasks
                'initializing':'build',
                'scheduling':'build',
                'spawning':'build',
                #Atmosphere Task-specific lines
                'networking':'build',
                'deploying':'build',
                'deploy_error':'build',
                #There are more.. Must find table..
        }
        new_status = task_status_map.get(task_name)
        logger.debug("Instance:%s History - Task provided:%s, Status should be %s"
                      % (self.provider_alias, task_name, new_status))
        return new_status


    def update_history(self, status_name, size, task=None, first_update=False):
        """
        Given the status name and size, look up the previous history object
        If nothing has changed: return (False, last_history)
        else: end date previous history object, start new history object.
              return (True, new_history)
        """
        #1. Get status name
        if task:
            new_status = self._task_to_status(task)
            #TODO: More validation needed.
            #suspended - deploy_error == build.. but thats not ideal.
            if new_status:
                status_name = new_status
        #2. Get the last history (or Build a new one if no other exists)
        last_history = self.get_last_history()
        if not last_history:
            last_history = InstanceStatusHistory.create_history(
                    status_name, self, size, self.start_date)
            last_history.save()
            logger.debug("First history: %s" % last_history)

        #2. Size and name must match to continue using last history
        if last_history.status.name == status_name and last_history.size.id == size.id:
            #logger.info("status_name matches last history:%s " %
            #        last_history.status.name)
            return (False, last_history)

        #3. ASSERT: A new history item is required due to a State or Size Change
        now_time = timezone.now()
        try:
            new_history = InstanceStatusHistory.transaction(
                    status_name, self, size,
                    start_time=now_time,
                    last_history=last_history)
            return (True, new_history)
        except ValueError, bad_transaction:
            logger.exception("Bad transaction")
            return (False, last_history)

    def get_active_hours(self):
        #Don't move it up. Circular reference.
        from service.allocation import delta_to_hours
        total_time = self._calculate_active_time()
        return delta_to_hours(total_time)

    def _calculate_active_time_d(self, delta):
        #from service.allocation import delta_to_hours
        status_history = self.instancestatushistory_set.all()
        now = timezone.now()
        if not status_history:
            # No status history, use entire length of instance
            # logger.info("First history update: %s starting %s" %
            #             (self.provider_alias, now))
            end_date = self.end_date if self.end_date else now
            return end_date - self.start_date
        #Start counting..
        threshold_date = now - delta
        total_time = timedelta()
        for state in status_history:
            if not state.is_active():
                continue
            if not state.end_date:
                # logger.debug("Status %s has no end-date." %
                #         state.status.name)
                state.end_date = timezone.now()
            if state.end_date < threshold_date:           
                #Ignore states that are pass the threshold
                continue                                  
            active_time = state.end_date - state.start_date
            new_total = active_time + total_time
            #logger.info("%s + %s = %s" %
            #        (delta_to_hours(active_time),
            #         delta_to_hours(total_time),
            #         delta_to_hours(new_total)))
            total_time = new_total
        return total_time
    def get_active_hours(self, delta):
        #Don't move it up. Circular reference.
        from service.allocation import delta_to_hours
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
        #Determine the earliest time to start counts.
        if not earliest_time:
            earliest_time = self.start_date

        total_time = timedelta()
        accounting_list = []
        last_history = self.get_last_history()
        active_history = self.recent_history(earliest_time, latest_time)

        for state in active_history:
            active_time = state.get_active_time(earliest_time, latest_time)
            state.active_time = active_time
            state.cpu_time = active_time * state.size.cpu
            accounting_list.append(state)
        return accounting_list



    def end_date_all(self):
        """
        Call this function to tie up loose ends when the instance is finished
        (Destroyed, terminated, no longer exists..)
        """
        now_time = timezone.now()
        ish_list = InstanceStatusHistory.objects.filter(instance=self)
        for ish in ish_list:
            if not ish.end_date:
#                logger.info('Saving history:%s' % ish)
                ish.end_date = now_time
                ish.save()
        if not self.end_date:
#            logger.info("Saving Instance:%s" % self)
            self.end_date = now_time
            self.save()

    def creator_name(self):
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
                if self.provider_machine:
                    return md5(self.provider_machine.identifier).hexdigest()
            except ProviderMachine.DoesNotExist as dne:
                logger.exception("Unable to find provider_machine for %s." % self.provider_alias)
        return 'Unknown'

    def esh_status(self):
        if self.esh:
            return self.esh.get_status()
        last_history = self.get_last_history()
        if last_history:
            return last_history.status.name
        else:
            return "Unknown"

    def esh_size(self):
        if not self.esh or not hasattr(self.esh._node, 'extra'):
            last_history = self.get_last_history()
            if last_history:
                return last_history.size.name
            return "Unknown"
        extras = self.esh._node.extra
        if extras.has_key('flavorId'):
            return extras['flavorId']
        elif extras.has_key('instance_type'):
            return extras['instance_type']
        elif extras.has_key('instancetype'):
            return extras['instancetype']
        else:
            return "Unknown"

    def esh_machine_name(self):
        return self.provider_machine.application.name

    def provider_id(self):
        return self.provider_machine.provider.id

    def provider_name(self):
        return self.provider_machine.provider.location

    def esh_machine(self):
        return self.provider_machine.identifier

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
             self.created_by, self.ip_address)

    class Meta:
        db_table = "instance"
        app_label = "core"


class InstanceStatus(models.Model):
    """
    Used to enumerate the types of actions
    (I.e. Stopped, Suspended, Active, Deleted)
    """
    name = models.CharField(max_length=128)

    def __unicode__(self):
        return "%s" % self.name

    class Meta:
        db_table = "instance_status"
        app_label = "core"


class InstanceStatusHistory(models.Model):
    """
    Used to keep track of each change in instance status
    (Useful for time management)
    """
    instance = models.ForeignKey(Instance)
    size = models.ForeignKey("Size", null=True, blank=True)
    status = models.ForeignKey(InstanceStatus)
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

    @classmethod
    def transaction(cls, status_name, instance, size,
                    start_time=None, last_history=None):
        try:
            with transaction.atomic():
                if not last_history:
                    last_history = instance.get_last_history()\
                                           .select_for_update(nowait=True)
                    if not last_history:
                        raise ValueError("A previous history is required "
                                         "to perform a transaction. Instance:%s"
                                         % (instance,))
                    elif last_history.end_date:
                        raise ValueError("Old history already has end date: %s"
                                         % last_history)
                last_history.end_date = start_time
                last_history.save()
                new_history = InstanceStatusHistory.create_history(
                    status_name, instance, size, start_time)
                logger.info("Status Update - User:%s Instance:%s Old:%s New:%s Time:%s"
                            % (instance.created_by, instance.provider_alias,
                               last_history.status.name, new_history.status.name,
                               new_history.start_date))
                new_history.save()
            return new_history
        except DatabaseError as dbe:
            logger.exception("instance_status_history: Lock is already acquired by"
                             "another transaction.")

    @classmethod
    def create_history(cls, status_name, instance, size, start_date=None):
        """
        Creates a new (Unsaved!) InstanceStatusHistory
        """
        status, _ = InstanceStatus.objects.get_or_create(name=status_name)
        new_history = InstanceStatusHistory(
            instance=instance, size=size, status=status)
        if start_date:
            new_history.start_date=start_date
            logger.debug("Created new history object: %s " % (new_history))
        return new_history

    def get_active_time(self, earliest_time=None, latest_time=None):
        """
        A set of filters used to determine the amount of 'active time'
        earliest_time and latest_time are taken into account, if provided.
        """
        # Inactive states are not counted against you.
        if not self.is_active():
            return timedelta()

        # When to start counting
        if earliest_time and self.start_date <= earliest_time:
            start_time = earliest_time
        else:
            start_time = self.start_date

        # When to stop counting.. Some history may have no end date!
        if latest_time:
            if not self.end_date or self.end_date >= latest_time:
                final_time = latest_time
                #TODO: Possibly check latest_time < timezone.now() to prevent
                #      bad input? 
            else:
                final_time = self.end_date
        elif self.end_date:
            final_time = self.end_date
        else:
            #This is the current status, so stop counting now..
            final_time = timezone.now()

        #Active time is easy now!
        active_time = final_time - start_time
        return active_time
    

    @classmethod
    def intervals(cls, instance, start_date=None, end_date=None):
        all_history = cls.objects.filter(instance=instance)
        if start_date and end_date:
            all_history = all_history.filter(start_date__range=[start_date,end_date])
        elif start_date:
            all_history = all_history.filter(start_date__gt=start_date)
        elif end_date:
            all_history = all_history.filter(end_date__lt=end_date)
        return all_history

    def __unicode__(self):
        return "%s (FROM:%s TO:%s)" % (self.status,
                               self.start_date,
                               self.end_date if self.end_date else '')

    def is_active(self):
        """
        Use this function to determine whether or not a specific instance
        status history should be considered 'active'
        """
        if self.status.name == 'active':
            return True
        else:
            return False

    class Meta:
        db_table = "instance_status_history"
        app_label = "core"



"""
Useful utility methods for the Core Model..
"""

def map_to_identity(core_instances):
    instance_id_map = {}
    for instance in core_instances:
        identity_id = instance.created_by_identity_id
        instance_list = instance_id_map.get(identity_id,[])
        instance_list.append(instance)
        instance_id_map[identity_id] = instance_list
    return instance_id_map

def find_instance(instance_id):
    core_instance = Instance.objects.filter(provider_alias=instance_id)
    if len(core_instance) > 1:
        logger.warn("Multiple instances returned for instance_id - %s" % instance_id)
    if core_instance:
        return core_instance[0]
    return None

def _find_esh_ip(esh_instance):
    try:
        ip_address = esh_instance._node.public_ips[0]
    except IndexError:  # no public ip
        try:
            ip_address = esh_instance._node.private_ips[0]
        except IndexError:  # no private ip
            ip_address = '0.0.0.0'
    return ip_address


def _update_core_instance(core_instance, ip_address, password):
    core_instance.ip_address = ip_address
    if password:
        core_instance.password = password
    core_instance.save()

def _find_esh_start_date(esh_instance):
    if 'launchdatetime' in esh_instance.extra:
        create_stamp = esh_instance.extra.get('launchdatetime')
    elif 'launch_time' in esh_instance.extra:
        create_stamp = esh_instance.extra.get('launch_time')
    elif 'created' in esh_instance.extra:
        create_stamp = esh_instance.extra.get('created')
    else:
        raise Exception("Instance does not have a created timestamp.  This"
        "should never happen. Don't cheat and assume it was created just "
        "now. Get the real launch time, bra.")
    start_date = _convert_timestamp(create_stamp)
    return start_date

def _convert_timestamp(create_stamp):
    # create_stamp is an iso 8601 timestamp string
    # that may or may not include microseconds.
    # start_date is a timezone-aware datetime object
    try:
        start_date = datetime.strptime(create_stamp, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        start_date = datetime.strptime(create_stamp, '%Y-%m-%dT%H:%M:%SZ')
    #All Dates are UTC relative
    start_date = start_date.replace(tzinfo=pytz.utc)
    logger.debug("Launched At: %s" % create_stamp)
    logger.debug("Started At: %s" % start_date)
    return start_date


def convert_esh_instance(esh_driver, esh_instance, provider_id, identity_id,
                         user, token=None, password=None):
    """
    """
    instance_id = esh_instance.id
    ip_address = _find_esh_ip(esh_instance)
    esh_machine = esh_instance.machine
    core_instance = find_instance(instance_id)
    if core_instance:
        _update_core_instance(core_instance, ip_address, password)
    else:
        start_date = _find_esh_start_date(esh_instance)
        logger.debug("Instance: %s" % instance_id)
        if type(esh_machine) == MockMachine:
            #MockMachine includes only the Alias/ID information
            #so a lookup on the machine is required to get accurate
            #information.
            esh_machine = esh_driver.get_machine(esh_machine.id)
        #Ensure that core Machine exists
        coreMachine = convert_esh_machine(esh_driver, esh_machine,
                                          provider_id, user,
                                          image_id=esh_instance.image_id)
        #Use New/Existing core Machine to create core Instance
        core_instance = create_instance(provider_id, identity_id, instance_id,
                                      coreMachine, ip_address,
                                      esh_instance.name, user,
                                      start_date, token, password)
    #Add 'esh' object
    core_instance.esh = esh_instance
    #Confirm instance exists in a project
    _check_project(core_instance, user)
    #Update the InstanceStatusHistory
    #NOTE: Querying for esh_size because esh_instance
    #Only holds the alias, not all the values.
    #As a bonus this is a cached-call
    esh_size = esh_instance.size
    if type(esh_size) == MockSize:
        #MockSize includes only the Alias/ID information
        #so a lookup on the size is required to get accurate
        #information.
        esh_size = esh_driver.get_size(esh_size.id)
    core_size = convert_esh_size(esh_size, provider_id)
    #TODO: You are the mole!
    core_instance.update_history(
        esh_instance.extra['status'],
        core_size,
        esh_instance.extra.get('task') or
        esh_instance.extra.get('metadata',{}).get('tmp_status'))
    #Update values in core with those found in metadata.
    core_instance = set_instance_from_metadata(esh_driver, core_instance)
    return core_instance

def _check_project(core_instance, user):
    """
    Select a/multiple projects the instance belongs to.
    NOTE: User (NOT Identity!!) Specific
    """
    core_projects = core_instance.get_projects(user)
    if not core_projects:
        default_proj = user.get_default_project()
        default_proj.instances.add(core_instance)
        core_projects = [default_proj]
    return core_projects


def set_instance_from_metadata(esh_driver, core_instance):
    #Fixes Dep. loop - Do not remove
    from api.serializers import InstanceSerializer
    #Breakout for drivers (Eucalyptus) that don't support metadata
    if not hasattr(esh_driver._connection, 'ex_get_metadata'):
        #logger.debug("EshDriver %s does not have function 'ex_get_metadata'"
        #            % esh_driver._connection.__class__)
        return core_instance
    try:
        esh_instance = esh_driver.get_instance(core_instance.provider_alias)
        if not esh_instance:
            return core_instance
        metadata =  esh_driver._connection.ex_get_metadata(esh_instance)
    except Exception, e:
        logger.exception("Exception retrieving instance metadata for %s" %
                core_instance.provider_alias)
        return core_instance

    #TODO: Match with actual instance launch metadata in service/instance.py
    #TODO: Probably better to redefine serializer as InstanceMetadataSerializer
    #TODO: Define a creator and their identity by the METADATA instead of
    # assuming its the person who 'found' the instance

    serializer = InstanceSerializer(core_instance, data=metadata,
                                    partial=True)
    if not serializer.is_valid():
        logger.warn("Encountered errors serializing metadata:%s"
                    % serializer.errors)
        return core_instance
    serializer.save()
    core_instance = serializer.object
    core_instance.esh = esh_instance
    return core_instance

def create_instance(provider_id, identity_id, provider_alias, provider_machine,
                   ip_address, name, creator, create_stamp,
                   token=None, password=None):
    #TODO: Define a creator and their identity by the METADATA instead of
    # assuming its the person who 'found' the instance
    identity = Identity.objects.get(id=identity_id)
    new_inst = Instance.objects.create(name=name,
                                       provider_alias=provider_alias,
                                       provider_machine=provider_machine,
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
    #NOTE: No instance_status_history here, because status is not passed
    return new_inst
