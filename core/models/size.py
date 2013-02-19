from django.db import models
from django.utils import timezone
from core.models.provider import Provider
from atmosphere.logger import logger

class Size(models.Model):
    """
    """
    esh = None # Special field that is filled out when converting an eshSize
    alias = models.CharField(max_length=256) # m1.medium
    name = models.CharField(max_length=256) # Medium Instance
    provider = models.ForeignKey(Provider)
    cpu = models.IntegerField()
    disk = models.IntegerField()
    mem = models.IntegerField()
    start_date = models.DateTimeField(default=timezone.now())
    end_date = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = "size"
        app_label = "core"
    def esh_total(self):
        try:
            return self.esh._size.extra['occupancy']['total']
        except (AttributeError, KeyError) as no_extras:
            return 1
    def esh_remaining(self):
        try:
            return self.esh._size.extra['occupancy']['remaining']
        except (AttributeError, KeyError) as no_extras:
            return 1

    def esh_occupancy(self):
        total = self.esh_total() 
        remaining = self.esh_remaining()
        used =  total - remaining
        return used * 100 / total

    def update(self, *args, **kwargs):
        """
        Allows for partial updating of the model
        """
        #Upload args into kwargs
        for arg in args:
            for (key,value) in arg.items():
                kwargs[key] = value
        #Update the values
        for key in kwargs.keys():
            setattr(self, key, kwargs[key])
        self.save()
        return self
    def __unicode__(self):
        return "alias=%s (id=%s|name=%s) - %s - cpu: %s mem: %s disk: %s end date: %s" % (self.alias,
                                                                           self.id,
                                                                           self.name,
                                                                           self.provider,
                                                                           self.cpu,
                                                                           self.mem,
                                                                           self.disk,
                                                                           self.end_date)

def convertEshSize(eshSize, provider_id, user):
    """
    """
    alias = eshSize._size.id 
    try:
        coreSize = Size.objects.get(alias=alias, provider__id=provider_id)
    except Size.DoesNotExist, dne:
        #Gather up the additional, necessary information to create a DB repr
        name = eshSize._size.name
        ram = eshSize._size.ram
        disk = eshSize._size.disk
        cpu = eshSize.cpu
        coreSize = createSize(name, alias, cpu, ram, disk, provider_id)
    coreSize.esh = eshSize
    return coreSize

def createSize(name, alias, cpu, mem, disk, provider_id):
    provider = Provider.objects.get(id=provider_id)
    size = Size.objects.create(name=name, alias=alias, cpu=cpu, mem=mem, disk=disk, provider=provider)
    return size
