"""
Service Quota model for atmosphere.
"""

from django.db import models

class Quota(models.Model):
    """
    Quota limits the amount of resources that can be used for a User/Group
    Quotas are set at the Identity Level in IdentityMembership
    """
    cpu = models.IntegerField(null=True, blank=True, default=16)  # In CPU Units
    memory = models.IntegerField(null=True, blank=True, default=128)  # In GB
    storage = models.IntegerField(null=True, blank=True, default=10)  # In GB
    # In #Volumes allowed
    storage_count = models.IntegerField(null=True, blank=True, default=1)
    # In #Suspended instances allowed
    suspended_count = models.IntegerField(null=True, blank=True, default=2)

    def __unicode__(self):
        return "CPU:%s, MEM:%s, DISK:%s DISK #:%s SUSPEND #:%s" %\
            (self.cpu, self.memory, self.storage,
             self.storage_count, self.suspended_count)

    @classmethod
    def max_quota(self, by_type='cpu'):
        """
        Select max quota (Default - Highest CPU count
        """
        from django.db.models import Max
        if not Quota.objects.all():
            return self.unreachable_quota()
        max_quota_by_type = Quota.objects.all().aggregate(
                                        Max(by_type))['%s__max' % by_type]
        quota = Quota.objects.filter(cpu=max_quota_by_type)[0]
        if quota.cpu <= self._meta.get_field('cpu').default:
            return self.unreachable_quota()
        return quota

    @classmethod
    def default_quota(self):
        return Quota.objects.get_or_create(
                **Quota.default_dict())[0]

    @classmethod
    def unreachable_quota(self):
        return Quota.objects.get_or_create(
                **Quota.unreachable_dict())[0]

    @classmethod
    def unreachable_dict(cls):
        return {
            'cpu': 128,
            'memory': 256,
            'storage': 1000,
            'storage_count': 10
        }
    @classmethod
    def default_dict(cls):
        return {
            'cpu': cls._meta.get_field('cpu').default,
            'memory': cls._meta.get_field('memory').default,
            'storage': cls._meta.get_field('storage').default,
            'storage_count': cls._meta.get_field('storage_count').default
        }

    class Meta:
        db_table = 'quota'
        app_label = 'core'


def has_cpu_quota(driver, quota, new_size=0):
    """
    True if the total number of CPU cores found on
    driver is less than or equal to Quota.cpu,
    otherwise False.
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


def has_mem_quota(driver, quota, new_size=0):
    """
    True if the total amount of RAM found on driver is
    less than or equal to Quota.mem, otherwise False.
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


def has_storage_quota(driver, quota, new_size=0):
    """
    True if the total size of volumes found on driver is
    less than or equal to Quota.storage, otherwise False.
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


def has_storage_count_quota(driver, quota, new_size=0):
    """
    True if the total size of volumes found on driver is
    greater than or equal to Quota.storage otherwise False.
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


def get_quota(identity_id):
    try:
        return Quota.objects.get(identitymembership__identity__id=identity_id)
    except Quota.DoesNotExist:
        return None
