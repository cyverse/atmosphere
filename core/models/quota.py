"""
Service Quota model for atmosphere.
"""

from django.db import models


class Quota(models.Model):
    """
    Quota limits the amount of resources that can be used for a User/Group
    Quotas are set at the Identity Level in IdentityMembership
    """
    cpu = models.IntegerField(null=True, blank=True, default=2)  # In CPU Units
    memory = models.IntegerField(null=True, blank=True, default=4)  # In GB
    storage = models.IntegerField(null=True, blank=True, default=50)  # In GB
    # In #Volumes allowed
    storage_count = models.IntegerField(null=True, blank=True, default=1)
    # In #Suspended instances allowed
    suspended_count = models.IntegerField(null=True, blank=True, default=2)

    def __unicode__(self):
        return "CPU:%s, MEM:%s, DISK:%s DISK #:%s" %\
            (self.cpu, self.memory, self.storage, self.storage_count)

    @classmethod
    def defaults(self):
        return {
            'cpu': self._meta.get_field('cpu').default,
            'memory': self._meta.get_field('memory').default,
            'storage': self._meta.get_field('storage').default,
            'storage_count': self._meta.get_field('storage_count').default
        }

    class Meta:
        db_table = 'quota'
        app_label = 'core'


def cpuQuotaTest(driver, quota, new_size=0):
    """
    Test if the total # of CPU cores found on driver is <= Quota.cpu
    """
    #Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    #Always True if cpu is null
    if not quota.cpu:
        return True
    total_size = new_size
    instances = driver.list_instances()
    for inst in instances:
        total_size += inst.size._size.extra['cpu']
    return total_size <= quota.cpu


def memQuotaTest(driver, quota, new_size=0):
    """
    Test if the total # of RAM found on driver is <= Quota.mem
    """
    #Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    #Always True if ram is null
    if not quota.ram:
        return True
    total_size = new_size
    instances = driver.list_instances()
    for inst in instances:
        total_size += inst.size._size.ram
    return total_size <= quota.memory


def storageQuotaTest(driver, quota, new_size=0):
    """
    Test if the total size of volumes found on driver is <= Quota.storage
    """
    #Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    #Always True if storage is null
    if not quota.storage:
        return True
    vols = driver.list_volumes()
    total_size = new_size
    for vol in vols:
        total_size += vol.size
    return total_size <= quota.storage


def storageCountQuotaTest(driver, quota, new_size=0):
    """
    Test if the total size of volumes found on driver is <= Quota.storage
    """
    #Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    #Always True if storage count is null
    if not quota.storage_count:
        return True
    num_vols = new_size
    num_vols += len(driver.list_volumes())
    return num_vols <= quota.storage_count


def getQuota(identity_id):
    try:
        return Quota.objects.get(identitymembership__identity__id=identity_id)
    except Quota.DoesNotExist:
        return None
