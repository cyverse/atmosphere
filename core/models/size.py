import uuid

from django.db import models
from django.utils import timezone
from core.models.provider import Provider


class Size(models.Model):

    """
    """
    # Special field that is filled out when converting an esh_size
    esh = None
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    alias = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    provider = models.ForeignKey(Provider)
    cpu = models.IntegerField()
    disk = models.IntegerField()
    root = models.IntegerField()
    mem = models.IntegerField()
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "size"
        app_label = "core"

    def esh_total(self):
        try:
            return self.esh.extra['occupancy']['total']
        except (AttributeError, KeyError):
            return 1

    def esh_remaining(self):
        try:
            return self.esh.extra['occupancy']['remaining']
        except (AttributeError, KeyError):
            return 1

    def esh_occupancy(self):
        total = self.esh_total()
        if total == 0:
            return 0
        remaining = self.esh_remaining()
        used = total - remaining
        return used * 100 / total

    def active(self):
        now = timezone.now()
        if self.start_date <= now:
            if not self.end_date:
                return True
            elif self.end_date >= now:
                return True
        return False

    def __unicode__(self):
        return "alias=%s \
                (id=%s|name=%s) - %s - \
                cpu: %s mem: %s disk: %s end date: %s" % (
            self.alias,
            self.id,
            self.name,
            self.provider_id,
            self.cpu,
            self.mem,
            self.disk,
            self.end_date)


def convert_esh_size(esh_size, provider_uuid):
    """
    """
    alias = esh_size.id
    try:
        core_size = Size.objects.get(alias=alias, provider__uuid=provider_uuid)
        core_size = _update_from_cloud_size(core_size, esh_size)
    except Size.DoesNotExist:
        # Gather up the additional, necessary information to create a DB repr
        try:
            provider = Provider.objects.get(uuid=provider_uuid)
        except Provider.DoesNotExist:
            raise Exception("Provider UUID: %s does not exist."
                            % provider_uuid)
        core_size = _create_from_cloud_size(esh_size, provider)
    # Attach esh after the save!
    core_size.esh = esh_size
    return core_size


def _update_from_cloud_size(core_size, esh_size):
    """
    Full scope replacement based on cloud(rtwo) size
    """
    core_size.name = esh_size.name
    core_size.disk = esh_size.disk
    core_size.root = esh_size.ephemeral
    core_size.cpu = esh_size.cpu
    core_size.mem = esh_size.ram
    core_size.save()
    return core_size


def _create_from_cloud_size(esh_size, provider):
    core_size = Size.objects.create(
        alias=esh_size.id,
        provider=provider,
        name=esh_size.name,
        disk=esh_size.disk,
        root=esh_size.ephemeral,
        cpu=esh_size.cpu,
        mem=esh_size.ram,
    )
    return core_size


def create_size(name, alias, cpu, mem, disk, root, provider_uuid):
    provider = Provider.objects.get(uuid=provider_uuid)
    size = Size.objects.create(
        name=name,
        alias=alias,
        cpu=cpu,
        mem=mem,
        disk=disk,
        root=root,
        provider=provider)
    return size
