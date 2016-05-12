"""
Service Quota model for atmosphere.
"""
import uuid

from django.conf import settings
from django.db import models

# Default functions to be allow for dynamic-defaults
# Values to the right will be used IF the configuration
# does not provide a value


def _get_default_cpu():
    return _get_default_quota('cpu', 16)


def _get_default_memory():
    return _get_default_quota('memory', 128)


def _get_default_storage():
    return _get_default_quota('storage', 10)


def _get_default_storage_count():
    return _get_default_quota('storage_count', 10)


def _get_default_port_count():
    return _get_default_quota('port', 10)


def _get_default_floating_ip_count():
    return _get_default_quota('floating_ip', 10)


def _get_default_instance_count():
    return _get_default_quota('instance_count', 10)


def _get_default_suspended_count():
    return _get_default_quota('suspended_count', 2)


def _get_default_quota(key, default_value=-1):
    if not hasattr(settings, 'DEFAULT_QUOTA'):
        return default_value
    config_quota = settings.DEFAULT_QUOTA
    if not config_quota or not isinstance(config_quota, dict):
        # Configuration not properly setup. Use default values.
        return default_value
    value = config_quota.get(key)
    if not value or not isinstance(value, int):
        return default_value
    return value


class Quota(models.Model):

    """
    Quota limits the amount of resources that can be used for a User/Group
    Quotas are set at the Identity Level in IdentityMembership
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # Quotas generally defined on all Providers
    cpu = models.IntegerField(
        null=True,
        blank=True,
        default=_get_default_cpu)  # In CPU Units
    memory = models.IntegerField(null=True, blank=True, default=_get_default_memory)  # In GB
    storage = models.IntegerField(null=True, blank=True, default=_get_default_storage)  # In GB
    # Networking quota (Depends on Provider)
    floating_ip_count = models.IntegerField(null=True, blank=True, default=_get_default_floating_ip_count)
    port_count = models.IntegerField(null=True, blank=True, default=_get_default_port_count)
    # Compute quota (Depends on Provider)
    storage_count = models.IntegerField(null=True, blank=True, default=_get_default_storage_count)
    instance_count = models.IntegerField(null=True, blank=True, default=_get_default_instance_count)
    suspended_count = models.IntegerField(null=True, blank=True, default=_get_default_suspended_count)

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
            'storage_count': 100,
            'instance_count': 100,
            'floating_ip_count': -1,
            'port_count': -1,
        }

    @classmethod
    def default_dict(cls):
        return {
            'cpu': cls._meta.get_field('cpu').default(),
            'memory': cls._meta.get_field('memory').default(),
            'storage': cls._meta.get_field('storage').default(),
            'floating_ip_count': cls._meta.get_field('floating_ip_count').default(),
            'port_count': cls._meta.get_field('port_count').default(),
            'storage_count': cls._meta.get_field('storage_count').default(),
            'instance_count': cls._meta.get_field('instance_count').default(),
            'suspended_count': cls._meta.get_field('suspended_count').default()
        }

    class Meta:
        db_table = 'quota'
        app_label = 'core'
        unique_together = ("cpu", "memory", "storage",
                           "floating_ip_count",
                           "port_count",
                           "instance_count",
                           "storage_count",
                           "suspended_count")


def has_cpu_quota(driver, quota, new_size=0):
    """
    True if the total number of CPU cores found on
    driver is less than or equal to Quota.cpu,
    otherwise False.
    """
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if cpu is null
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
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if ram is null
    if not quota.ram:
        return True
    total_size = new_size
    instances = driver.list_instances()
    for inst in instances:
        total_size += inst.size._size.ram
    return total_size <= quota.memory


def has_instance_count_quota(driver, quota, new_size=0):
    """
    True if the total number of instances found on driver are
    greater than or equal to Quota.instance otherwise False.
    """
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if instance count is null
    if not quota.instance_count:
        return True
    num_insts = new_size
    num_insts += len(driver.list_instances())
    return num_insts <= quota.instance_count


def has_port_count_quota(driver, quota, new_size=0):
    """
    True if the total number of ports found on driver are
    less than or equal to Quota.port_count, otherwise False.
    """
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if port_count is null
    if not quota.port_count or quota.port_count < 0:
        return True
    ports = driver._connection.neutron_list_port_count()
    total_size = new_size
    total_size += len(ports)
    return total_size <= quota.port_count


def has_floating_ip_count_quota(driver, quota, new_size=0):
    """
    True if the total number of floating ips found on driver are
    less than or equal to Quota.floating_ip_count, otherwise False.
    """
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if floating_ip_count is null
    if not quota.floating_ip_count or quota.floating_ip_count < 0:
        return True
    floating_ips = driver._connection.ex_list_floating_ips()
    total_size = len(floating_ips)
    return total_size <= quota.floating_ip_count


def has_storage_quota(driver, quota, new_size=0):
    """
    True if the total volume size found on driver is
    less than or equal to Quota.storage, otherwise False.
    """
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if storage is null
    if not quota.storage:
        return True
    vols = driver.list_volumes()
    total_size = new_size
    for vol in vols:
        total_size += vol.size
    return total_size <= quota.storage


def has_storage_count_quota(driver, quota, new_size=0):
    """
    True if the total number of volumes found on driver are
    greater than or equal to Quota.storage otherwise False.
    """
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if storage count is null
    if not quota.storage_count:
        return True
    num_vols = new_size
    num_vols += len(driver.list_volumes())
    return num_vols <= quota.storage_count


def get_quota(identity_uuid):
    try:
        return Quota.objects.get(
            identitymembership__identity__uuid=identity_uuid)
    except Quota.DoesNotExist:
        return None
