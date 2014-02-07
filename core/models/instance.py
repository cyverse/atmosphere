"""
  Instance model for atmosphere.
"""
import pytz
import time
from hashlib import md5
from datetime import datetime, timedelta

from django.db import models
#from django.contrib.auth.models import User
#from core.models import AtmosphereUser as User
from django.utils import timezone

from threepio import logger

from core.models.identity import Identity
from core.models.machine import ProviderMachine, convert_esh_machine
from core.models.tag import Tag


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

    def last_history(self):
        """
        Returns the newest InstanceStatusHistory
        """
        last_hist = InstanceStatusHistory.objects\
                .filter(instance=self).order_by('-start_date')
        if not last_hist:
            return None
        return last_hist[0]

    def new_history(self, status_name, start_date=None):
        """
        Creates a new (Unsaved!) InstanceStatusHistory
        """
        new_hist = InstanceStatusHistory()
        new_hist.instance = self
        new_hist.status, created = InstanceStatus.objects\
                                      .get_or_create(name=status_name)
        if start_date:
            new_hist.start_date=start_date
#        logger.debug("Created new history object: %s " % (new_hist))
        return new_hist

    def update_history(self, status_name, task=None, first_update=False):
        if task:
            task_to_status = {
                    'resuming':'active',
                    'suspending':'suspended',
                    'powering-on':'active',
                    'powering-off':'suspended',
                    #Tasks that occur during the normal build process
                    'initializing':'build',
                    'scheduling':'build',
                    'spawning':'build',
                    #Atmosphere Task-specific lines
                    'networking':'build',
                    'deploying':'build',
                    #There are more.. Must find table..
            }
            status_2 = task_to_status.get(task,'')
            # logger.debug("Task provided:%s, Status should be %s"
            #              % (task, status_2))
            #Update to the more relevant task
            if status_2:
                status_name = status_2

        last_hist = self.last_history()
        #1. Build an active status if this is the first time
        if not last_hist:
            #This is the first status
            if first_update or status_name in ['build', 'pending', 'running']:
                #First update, just assign the 'normal' status..
                first_status = status_name
            else:
                #Not the first update, so we must
                #Assume instance was Active from start of instance to now
                first_status = 'active'
            first_hist = self.new_history(first_status, self.start_date)
            first_hist.save()
#            logger.debug("Created the first history %s" % first_hist)
            last_hist = first_hist
        #2. If we wanted to assign active status, thats done now.
        if last_hist.status.name == status_name:
            #logger.info("status_name matches last history:%s " %
            #        last_hist.status.name)
            return
        #3. ASSERT: A status update is required (Non-active state)
        now_time = timezone.now()
        last_hist.end_date = now_time
        last_hist.save()
        new_hist = self.new_history(status_name, now_time)
        new_hist.save()

    def get_active_hours(self):
        #Don't move it up. Circular reference.
        from service.allocation import delta_to_hours
        total_time = self._calculate_active_time()
        return delta_to_hours(total_time)

    def get_active_time(self):
        total_time = self._calculate_active_time()
        return total_time

    def _calculate_active_time(self):
        #from service.allocation import delta_to_hours
        status_history = self.instancestatushistory_set.all()
        if not status_history:
            # No status history, use entire length of instance
            now = timezone.now()
            # logger.info("First history update: %s starting %s" %
            #             (self.provider_alias, now))
            end_date = self.end_date if self.end_date else now
            return end_date - self.start_date
        #Start counting..
        total_time = timedelta()
        for state in status_history:
            if not state.is_active():
                continue
            if not state.end_date:
                # logger.debug("Status %s has no end-date." %
                #         state.status.name)
                state.end_date = timezone.now()
            active_time = state.end_date - state.start_date
            new_total = active_time + total_time
            #logger.info("%s + %s = %s" % 
            #        (delta_to_hours(active_time), 
            #         delta_to_hours(total_time),
            #         delta_to_hours(new_total)))
            total_time = new_total
        return total_time

        

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
        return "Unknown"

    def esh_size(self):
        if not self.esh or not hasattr(self.esh._node, 'extra'):
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
    status = models.ForeignKey(InstanceStatus)
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

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


def convert_esh_instance(esh_driver, esh_instance, provider_id, identity_id,
                         user, token=None, password=None):
    """
    """
    #logger.debug(esh_instance.__dict__)
    #logger.debug(esh_instance.extra)
    try:
        ip_address = esh_instance._node.public_ips[0]
    except IndexError:  # no public ip
        try:
            ip_address = esh_instance._node.private_ips[0]
        except IndexError:  # no private ip
            ip_address = '0.0.0.0'
    eshMachine = esh_instance.machine
    instance_id = esh_instance.id
    core_instance = find_instance(instance_id)
    if core_instance:
        core_instance.ip_address = ip_address
        if password:
            core_instance.password = password
        core_instance.save()
    else:
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

        # create_stamp is an iso 8601 timestamp string that may or may not
        # include microseconds start_date is a timezone-aware datetime object
        try:
            start_date = datetime.strptime(create_stamp, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            start_date = datetime.strptime(create_stamp, '%Y-%m-%dT%H:%M:%SZ')
        start_date = start_date.replace(tzinfo=pytz.utc)

        logger.debug("Instance %s" % instance_id)
        logger.debug("CREATED: %s" % create_stamp)
        logger.debug("START: %s" % start_date)
        coreMachine = convert_esh_machine(esh_driver, eshMachine, provider_id,
                                        image_id=esh_instance.image_id)
        core_instance = create_instance(provider_id, identity_id, instance_id,
                                      coreMachine, ip_address,
                                      esh_instance.name, user,
                                      start_date, token, password)

    core_instance.esh = esh_instance

    core_instance = set_instance_from_metadata(esh_driver, core_instance)
    return core_instance

def set_instance_from_metadata(esh_driver, core_instance):
    #Fixes Dep. loop - Do not remove
    from api.serializers import InstanceSerializer
    #Breakout for drivers (Eucalyptus) that don't support metadata
    if not hasattr(esh_driver._connection, 'ex_get_metadata'):
        #logger.debug("EshDriver %s does not have function 'ex_get_metadata'"
        #            % esh_driver._connection.__class__)
        return core_instance
    esh_instance = esh_driver.get_instance(core_instance.provider_alias)
    if not esh_instance:
        return core_instance
    metadata =  esh_driver._connection.ex_get_metadata(esh_instance)

    #TODO: Match with actual instance launch metadata in service/instance.py
    #TODO: Probably better to redefine serializer as InstanceMetadataSerializer
    #TODO: Define a creator and their identity by the METADATA instead of
    # assuming its the person who 'found' the instance

    serializer = InstanceSerializer(core_instance, data=metadata, partial=True)
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
