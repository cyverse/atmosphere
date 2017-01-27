"""
Service Quota model for atmosphere.
"""
import uuid

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

from threepio import logger

# Default functions to be allow for dynamic-defaults
# Values to the right will be used IF the configuration
# does not provide a value


def _get_default_cpu():
    return _get_default_quota('cpu', 16)


def _get_default_memory():
    return _get_default_quota('memory', 128)


def _get_default_storage():
    return _get_default_quota('storage', 10)


def _get_default_snapshot_count():
    return _get_default_quota('snapshot_count', 10)


def _get_default_storage_count():
    return _get_default_quota('storage_count', 10)


def _get_default_port_count():
    return _get_default_quota('fixed_ip_count', 10)


def _get_default_floating_ip_count():
    return _get_default_quota('floating_ip_count', 10)


def _get_default_instance_count():
    return _get_default_quota('instance_count', 10)


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
    # Compute quota (Depends on Provider)
    instance_count = models.IntegerField(null=True, blank=True, default=_get_default_instance_count)
    # Volume quota (Depends on Provider)
    snapshot_count = models.IntegerField(null=True, blank=True, default=_get_default_snapshot_count)
    storage_count = models.IntegerField(null=True, blank=True, default=_get_default_storage_count)
    # Networking quota (Depends on Provider)
    floating_ip_count = models.IntegerField(null=True, blank=True, default=_get_default_floating_ip_count)
    port_count = models.IntegerField(null=True, blank=True, default=_get_default_port_count)

    def __unicode__(self):
        str_builder = "ID:%s UUID:%s - " % (self.id, self.uuid)
        str_builder += "CPU:%s, Memory:%s GB, Volume:%s GB " %\
            (self.cpu, self.memory, self.storage)
        str_builder += "Instances #:%s " %\
            (self.instance_count,)
        str_builder += "Volume #:%s Snapshot #:%s " %\
            (self.storage_count, self.snapshot_count)
        str_builder += "Floating IP #:%s Port #:%s" %\
            (self.floating_ip_count, self.port_count)
        return str_builder

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
            'snapshot_count': 100,
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
            'instance_count': cls._meta.get_field('instance_count').default(),
            'storage_count': cls._meta.get_field('storage_count').default(),
            'snapshot_count': cls._meta.get_field('snapshot_count').default(),
        }

    class Meta:
        db_table = 'quota'
        app_label = 'core'


def has_cpu_quota(driver, quota, new_size=0, raise_exc=True):
    """
    True if the total number of CPU cores found on
    driver is less than or equal to Quota.cpu,
    otherwise False.
    """
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if cpu is null
    if not quota.cpu or quota.cpu < 0:
        return True
    total_size = new_size
    _pre_cache_sizes(driver)
    instances = driver.list_instances()
    for inst in instances:
        try:
            total_size += inst.size._size.extra['cpu']
        except AttributeError, KeyError:
            # Instance running on an unknown size..
            total_size += 1
    if total_size <= quota.cpu:
        return True
    if raise_exc:
        _raise_quota_error('CPU', total_size - new_size, new_size, quota.cpu)
    return False


def has_mem_quota(driver, quota, new_size=0, raise_exc=True):
    """
    True if the total amount of RAM found on driver is
    less than or equal to Quota.mem, otherwise False.
    """
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if ram is null
    if not quota.memory or quota.memory < 0:
        return True
    total_size = new_size/1024.0
    _pre_cache_sizes(driver)
    instances = driver.list_instances()
    for inst in instances:
        try:
            total_size += inst.size._size.ram / 1024.0
        except AttributeError, KeyError:
            # Instance running on an unknown size..
            total_size += 1
    total_size = int(total_size)
    if total_size <= quota.memory:
        return True
    if raise_exc:
        _raise_quota_error('Memory', (total_size - new_size)/1024.0, new_size/1024.0, quota.memory)
    return False


def has_instance_count_quota(driver, quota, new_size=0, raise_exc=True):
    """
    True if the total number of instances found on driver are
    greater than or equal to Quota.instance otherwise False.
    """
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if instance count is null
    if not quota.instance_count or quota.instance_count < 0:
        return True
    total_size = new_size
    total_size += len(driver.list_instances())
    if total_size <= quota.instance_count:
        return True
    if raise_exc:
        _raise_quota_error('Instance', total_size - new_size, new_size, quota.instance_count)
    return False


def has_port_count_quota(identity, driver, quota, new_size=0, raise_exc=True):
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
    # Consider it true if we fail to connect here
    try:
        from service.instance import _to_network_driver
        network_driver = _to_network_driver(identity)
        port_list = network_driver.list_ports()
    except Exception as exc:
        logger.warn("Could not verify quota due to failed call to network_driver.list_ports() - %s" % exc)
        return True

    fixed_ips = [port for port in port_list if 'compute:' in port['device_owner']]
    total_size = new_size
    total_size += len(fixed_ips)
    if total_size <= quota.port_count:
        return True
    if raise_exc:
        _raise_quota_error('Fixed IP', total_size - new_size, new_size, quota.port_count)
    return False


def has_floating_ip_count_quota(driver, quota, new_size=0, raise_exc=True):
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
    total_size = new_size
    total_size += len(floating_ips)
    if total_size <= quota.floating_ip_count:
        return True
    if raise_exc:
        _raise_quota_error('Floating IP', total_size - new_size, new_size, quota.floating_ip_count)
    return False


def has_storage_quota(driver, quota, new_size=0, raise_exc=True):
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
    if total_size <= quota.storage:
        return True
    if raise_exc:
        _raise_quota_error('Storage Size', total_size - new_size, new_size, quota.storage)
    return False



def has_snapshot_count_quota(driver, quota, new_size=0, raise_exc=True):
    """
    True if the total number of volumes found on driver are
    greater than or equal to Quota.snapshot otherwise False.
    """
    # Always False if quota doesnt exist, new size is negative
    if not quota or new_size < 0:
        return False
    # Always True if snapshot count is null
    if not quota.snapshot_count or quota.snapshot_count < 0:
        return True
    total_size = new_size
    total_size += len(driver._connection.ex_list_snapshots())
    if total_size <= quota.snapshot_count:
        return True
    if raise_exc:
        _raise_quota_error('Snapshot', total_size - new_size, new_size, quota.snapshot_count)
    return False


def has_storage_count_quota(driver, quota, new_size=0, raise_exc=True):
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
    total_size = new_size
    total_size += len(driver.list_volumes())
    if total_size <= quota.storage_count:
        return True
    if raise_exc:
        _raise_quota_error('Volume', total_size - new_size, new_size, quota.storage_count)
    return False


def _raise_quota_error(resource_name, current_count, new_count, limit_count):
    raise ValidationError(
        "%s Quota Exceeded: Using %s + Requested %s but limited to %s"
        % (resource_name, current_count, new_count, limit_count))


def _pre_cache_sizes(driver):
    """
    Pre-caching sizes is required to get 'extra' data from size,
    rather than MockSize (default)
    """
    cached_sizes = driver.provider.sizeCls.sizes.get(driver.provider.identifier)
    if not cached_sizes:
        driver.list_sizes()
    return

def get_quota(identity_uuid):
    try:
        return Quota.objects.get(identity__uuid=identity_uuid)
    except Quota.DoesNotExist:
        return None
