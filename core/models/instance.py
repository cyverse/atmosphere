"""
  Instance model for atmosphere.
"""
import pytz
from hashlib import md5
from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from threepio import logger

from core.models.identity import Identity
from core.models.machine import ProviderMachine, convertEshMachine
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
    created_by = models.ForeignKey(User)
    created_by_identity = models.ForeignKey(Identity, null=True)
    shell = models.BooleanField()
    vnc = models.BooleanField()
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
        return new_hist

    def update_history(self, status_name, task=None, first_update=False):
        if task:
            task_to_status = {
                    'suspending':'suspended',
                    'resuming':'active',
                    'stopping':'suspended',
                    'starting':'active',
                    'deploying':'build',
                    'networking':'build',
                    'initializing':'build',
                    'scheduling':'build',
                    'spawning':'build',
                    #There are more.. Must find table..
            }
            status_2 = task_to_status.get(task,'')
            #Update to the more relevant task
            if status_2:
                status_name = status_2

        last_hist = self.last_history()
        #1. Build an active status if this is the first time
        if not last_hist:
            #This is the first status
            if first_update:
                #First update, just assign the 'normal' status..
                first_status = status_name
            else:
                #Not the first update, so we must
                #Assume instance was Active from start of instance to now
                first_status = 'active'
            first_hist = self.new_history(first_status, self.start_date)
            first_hist.save()
            logger.info("Created the first history %s" % first_hist)
            last_hist = first_hist
        #2. If we wanted to assign active status, thats done now.
        if last_hist.status.name == status_name:
            logger.info("status_name matches last history:%s " % last_hist)
            return
        #3. ASSERT: A status update is required (Non-active state)
        logger.info("Update required: History:%s != %s " % (last_hist,
                status_name))
        now_time = timezone.now()
        last_hist.end_date = now_time
        last_hist.save()
        new_hist = self.new_history(status_name, now_time)
        new_hist.save()
        

    def end_date_all(self):
        """
        Call this function to tie up loose ends when the instance is finished
        (Destroyed, terminated, no longer exists..)
        """
        now_time = timezone.now()
        if not self.end_date:
            self.end_date = now_time
            self.save()
        ish_list = InstanceStatusHistory.objects.filter(instance=self)
        for ish in ish_list:
            if not ish.end_date:
                ish.end_date = now_time
                ish.save()

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
        if self.esh:
            return self.esh._node.extra['instancetype']
        
        return "Unknown"

    def esh_machine_name(self):
        if self.esh and self.esh.machine:
            return self.esh.machine.name
        else:
            try:
                if self.provider_machine and self.provider_machine.machine:
                    return self.provider_machine.machine.name
            except ProviderMachine.DoesNotExist as dne:
                logger.exception("Unable to find provider_machine for %s." % self.provider_alias)
        return "Unknown"

    def esh_machine(self):
        if self.esh:
            return self.esh._node.extra['imageId']
        else:
            try:
                if self.provider_machine:
                    return self.provider_machine.identifier
            except ProviderMachine.DoesNotExist as dne:
                logger.exception("Unable to find provider_machine for %s." % self.provider_alias)
        return "Unknown"

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

def findInstance(alias):
    core_instance = Instance.objects.filter(provider_alias=alias)
    if len(core_instance) > 1:
        logger.warn("Multiple instances returned for alias - %s" % alias)
    if core_instance:
        return core_instance[0]
    return None


def convertEshInstance(esh_driver, esh_instance, provider_id, identity_id, user, token=None):
    """
    """
    #logger.debug(esh_instance.__dict__)
    #logger.debug(esh_instance.extra)
    alias = esh_instance.alias
    try:
        ip_address = esh_instance._node.public_ips[0]
    except IndexError:  # no public ip
        try:
            ip_address = esh_instance._node.private_ips[0]
        except IndexError:  # no private ip
            ip_address = '0.0.0.0'
    eshMachine = esh_instance.machine
    core_instance = findInstance(alias)
    if core_instance:
        core_instance.ip_address = ip_address
        core_instance.save()
    else:
        if 'launchdatetime' in esh_instance.extra:
            create_stamp = esh_instance.extra.get('launchdatetime')
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

        logger.debug("Instance %s" % alias)
        logger.debug("CREATED: %s" % create_stamp)
        logger.debug("START: %s" % start_date)

        coreMachine = convertEshMachine(esh_driver, eshMachine, provider_id,
                                        image_id=esh_instance.image_id)
        core_instance = createInstance(provider_id, identity_id, alias,
                                      coreMachine, ip_address,
                                      esh_instance.name, user,
                                      start_date, token)

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
    esh_instance = core_instance.esh
    metadata =  esh_driver._connection.ex_get_metadata(esh_instance)
    serializer = InstanceSerializer(core_instance, data=metadata, partial=True)
    if not serializer.is_valid():
        logger.warn("Encountered errors serializing metadata:%s"
                    % serializer.errors)
        return core_instance
    serializer.save()
    core_instance = serializer.object
    core_instance.esh = esh_instance
    return core_instance

def update_instance_metadata(esh_driver, esh_instance, data={}, replace=True):
    """
    NOTE: This will NOT WORK for TAGS until openstack
    allows JSONArrays as values for metadata!
    """
    if not hasattr(esh_driver._connection, 'ex_set_metadata'):
        logger.info("EshDriver %s does not have function 'ex_set_metadata'"
                    % esh_driver._connection.__class__)
        return {}

    if data.get('name'):
        esh_driver._connection.ex_set_server_name(esh_instance, data['name'])
    try:
        return esh_driver._connection.ex_set_metadata(esh_instance, data,
                replace_metadata=replace)
    except Exception, e:
        if 'incapable of performing the request' in e.message:
            return {}
        else:
            raise

def createInstance(provider_id, identity_id, provider_alias, provider_machine,
                   ip_address, name, creator, create_stamp, token=None):
    identity = Identity.objects.get(id=identity_id)
    new_inst = Instance.objects.create(name=name,
                                       provider_alias=provider_alias,
                                       provider_machine=provider_machine,
                                       ip_address=ip_address,
                                       created_by=creator,
                                       created_by_identity=identity,
                                       token=token,
                                       start_date=create_stamp)
    new_inst.save()
    logger.debug("New instance created - %s (Token = %s)" %
                 (provider_alias, token))
    #NOTE: No instance_status_history here, because status is not passed
    return new_inst
