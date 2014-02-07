from django.db import models
from django.utils import timezone
from core.models.provider import Provider


class Size(models.Model):
    """
    """
    # Special field that is filled out when converting an esh_size
    esh = None
    alias = models.CharField(max_length=256)
    name = models.CharField(max_length=256)
    provider = models.ForeignKey(Provider)
    cpu = models.IntegerField()
    disk = models.IntegerField()
    root = models.IntegerField()
    mem = models.IntegerField()
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "size"
        app_label = "core"

    def esh_total(self):
        try:
            return self.esh._size.extra['occupancy']['total']
        except (AttributeError, KeyError):
            return 1

    def esh_remaining(self):
        try:
            return self.esh._size.extra['occupancy']['remaining']
        except (AttributeError, KeyError):
            return 1

    def esh_occupancy(self):
        total = self.esh_total()
        if total == 0:
            return 0
        remaining = self.esh_remaining()
        used = total - remaining
        return used * 100 / total

    def update(self, *args, **kwargs):
        """
        Allows for partial updating of the model
        """
        #Upload args into kwargs
        for arg in args:
            for (key, value) in arg.items():
                kwargs[key] = value
        #Update the values
        for key in kwargs.keys():
            setattr(self, key, kwargs[key])
        self.save()
        return self

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
            self.provider,
            self.cpu,
            self.mem,
            self.disk,
            self.end_date)


def convert_esh_size(esh_size, provider_id):
    """
    """
    alias = esh_size._size.id
    try:
        core_size = Size.objects.get(alias=alias, provider__id=provider_id)
        new_esh_data = {
            'name': esh_size._size.name,
            'mem': esh_size._size.ram,
            'root': esh_size._size.disk,
            'disk': esh_size.ephemeral,
            'cpu': esh_size.cpu,
        }
        #Update changed values..
        core_size.update(**new_esh_data)
    except Size.DoesNotExist:
        #Gather up the additional, necessary information to create a DB repr
        name = esh_size._size.name
        ram = esh_size._size.ram
        disk = esh_size._size.disk
        root = esh_size.ephemeral
        cpu = esh_size.cpu
        core_size = create_size(name, alias, cpu, ram, disk, root, provider_id)
    core_size.esh = esh_size
    return core_size


def create_size(name, alias, cpu, mem, disk, root, provider_id):
    provider = Provider.objects.get(id=provider_id)
    size = Size.objects.create(
        name=name,
        alias=alias,
        cpu=cpu,
        mem=mem,
        disk=disk,
        root=root,
        provider=provider)
    return size
