"""
Service Provider model for atmosphere.
"""
# vim: tabstop=2 expandtab shiftwidth=2 softtabstop=2

from django.db import models
from django.utils import timezone
#from core.models.group import Group
from core.models.quota import Quota

class ProviderType(models.Model):
    """
    Keep track of Provider via type
    """
    name = models.CharField(max_length=256) # AWS
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)
    def json(self):
        return {
            'name':self.name
            }
    class Meta:
        db_table = 'provider_type'
        app_label = 'core'
    def __unicode__(self):
        return self.name

class ProviderSize(models.Model):
    #TODO: :Fix the providersize model to have a foreign key to Provider..
    """
    ProviderSize is the resource amount allocated to a machine when an instance has launched.
    The alias' are different for each provider and the information necessary in each size depends on the provider.
    The current model includes CPU Units/RAM (In GB)/HDD Space (In GB)
    Start date and end date are recorded for logging purposes

    Optional fields include:
      Bandwidth
      Price
    """
    esh = None # Special field that is filled out when converting an eshSize
    name = models.CharField(max_length=256) # Medium Instance
    alias = models.CharField(max_length=256) # m1.medium
    cpu = models.IntegerField(null=True, blank=True)
    ram = models.IntegerField(null=True, blank=True)
    disk = models.IntegerField(null=True, blank=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = 'provider_size'
        app_label = 'core'

class Provider(models.Model):
    """
    Detailed information about a provider
    Providers have a specific location (Human readable to describe where/what cloud it is)
    Active providers are "Online", Inactive providers are shown as "Offline" in the frontend and API requests.
    Start date and end date are recorded for logging purposes
    """
    location = models.CharField(max_length=256)  #AWS West Coast
    type = models.ForeignKey(ProviderType)
    active = models.BooleanField(default=True) #For easy maintenance
    public = models.BooleanField(default=False) # Internal//External Cloud
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(blank=True, null=True)
    def __unicode__(self):
        return "%s:%s" % (self.id,self.location)
    class Meta:
        db_table = 'provider'
        app_label = 'core'
