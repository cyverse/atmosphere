"""
  Instance model for atmosphere.
"""
from hashlib import md5
from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from core.models.machine import ProviderMachine, convertEshMachine
from core.models.tag import Tag
from atmosphere.logger import logger


class Instance(models.Model):
    """
    When a user launches a machine, an Instance is created.
    Instances are described by their Name and associated Tags
    Instances have a specific ID of the machine they were created from (Provider Machine)
    Instances have a specific ID of their own (Provider Alias)
    The IP Address, creation and termination date, and the user who launched the instance are recorded for logging purposes.
    """
    esh = None # Custom field that is only active when a 'core' model has been converted.
    name = models.CharField(max_length=256)
    #TODO: Create custom Uuidfield?
    token = models.CharField(max_length=36, blank=True, null=True)#A secondary key to lookup an instance without knowing its alias
    tags = models.ManyToManyField(Tag)
    provider_machine = models.ForeignKey(ProviderMachine) # The specific machine & provider for which this instance exists
    provider_alias = models.CharField(max_length=256) #i-12341234 emi-E6411DC4 ami-cbfda58e
    ip_address = models.GenericIPAddressField(null=True, unpack_ipv4=True) #128.196.111.000
    created_by = models.ForeignKey(User) #The specific user that initiated the launch
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True)

    def creator_name(self):
        return self.created_by.username
    def hash_alias(self):
        return md5(self.provider_alias).hexdigest()
    def hash_machine_alias(self):
        return md5(self.esh._node.extra['imageId']).hexdigest()
    def esh_status(self):
        if not self.esh:
            return "Unknown"
        #TODO: If openstack: Use extra['task'] and extra['power'] to determine the appropriate status.
        status = self.esh._node.extra['status']
        if self.esh._node.extra.has_key('task') and self.esh._node.extra['task']:
            status += ' - %s' % self.esh._node.extra['task']
        return status
    def esh_size(self):
        if not self.esh:
            return "Unknown"
        return self.esh._node.extra['instancetype']
    def esh_machine_name(self):
        if not self.esh:
            return "Unknown"
        return self.esh.machine.name

    def esh_machine(self):
        if not self.esh:
            return "Unknown"
        return self.esh._node.extra['imageId']

    def json(self):
        return {
                'alias':self.provider_alias,
                'name':self.name,
                'tags':[tag.json() for tag in self.tags.all()],
                'ip_address':self.ip_address,
                'provider_machine':self.provider_machine.json(),
                'created_by':self.created_by.username,
        }
    def __unicode__(self):
        return "%s (Name:%s, Creator:%s, IP:%s)" % (self.provider_alias,self.name,self.created_by,self.ip_address)
    class Meta:
        db_table = "instance"
        app_label = "core"

"""
Useful utility methods for the Core Model..
"""
def findInstance(alias):
    coreInstance = Instance.objects.filter(provider_alias=alias)
    if len(coreInstance) > 1:
        logger.warn("Multiple instances returned for alias - %s" % alias)
    if coreInstance:
        return coreInstance[0]
    return None

def convertEshInstance(eshInstance, provider_id, user, token=None):
    """
    """
    alias = eshInstance.alias
    try:
        ip_address = eshInstance._node.public_ips[0]
    except IndexError, no_public_ip:
        try:
            ip_address = eshInstance._node.private_ips[0]
        except IndexError, no_ips:
            ip_address = '0.0.0.0'
    eshMachine = eshInstance.machine
    coreInstance = findInstance(alias)
    if coreInstance:
        coreInstance.ip_address = ip_address
        coreInstance.save()
    else:
        create_stamp = eshInstance.extra.get('launchdatetime')
        #if not create_stamp:
        #Openstack?
        coreMachine = convertEshMachine(eshMachine, provider_id)
        coreInstance = createInstance(provider_id, alias, coreMachine, ip_address, eshInstance.name, user, create_stamp, token)

    coreInstance.esh = eshInstance

    return coreInstance

def createInstance(provider_id, provider_alias, provider_machine, ip_address, name, creator, create_stamp, token=None):

    new_inst = Instance.objects.create(name=name, provider_alias=provider_alias, provider_machine=provider_machine, ip_address=ip_address, created_by=creator, token=token)

    create_date = datetime.strptime(create_stamp, '%Y-%m-%dT%H:%M:%S.%fZ')
    new_inst.start_date = create_date
    new_inst.save()

    logger.debug("New instance created - %s (Token = %s)" % (provider_alias, token))
    return new_inst
