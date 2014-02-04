from django.db import models
from django.utils import timezone
from uuid import uuid5, UUID
from threepio import logger

from atmosphere import settings

from core.models.identity import Identity
from core.models.tag import Tag, updateTags
from core.metadata import _get_admin_owner

class Application(models.Model):
    """
    An application is a collection of providermachines, where each
    providermachine represents a single revision, together forming a linear
    sequence of versions. The created_by field here is used for logging only;
    do not rely on it for permissions; use ApplicationMembership instead.
    """
    uuid = models.CharField(max_length=36, unique=True)
    name = models.CharField(max_length=256)
    description = models.TextField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    icon = models.ImageField(upload_to="machine_images", null=True, blank=True)
    private = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    # User/Identity that created the application object
    created_by = models.ForeignKey('AtmosphereUser')
    created_by_identity = models.ForeignKey(Identity, null=True)

    def icon_url(self):
        return self.icon.url if self.icon else None

    def get_provider_machines(self):
        pms = self.providermachine_set.all()
        return [{
            "start_date":pm.start_date,
            "end_date":pm.end_date,
            "alias":pm.identifier,
            "version":pm.version,
            "provider":pm.provider.id} for pm in pms]

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
            if key == 'tags':
                if type(kwargs[key]) != list:
                    tags_list = kwargs[key].split(",")
                else:
                    tags_list = kwargs[key]
                updateTags(self, tags_list)
                continue
            setattr(self, key, kwargs[key])
        self.save()
        return self

    def __unicode__(self):
        return "%s" % (self.name,)

    class Meta:
        db_table = 'application'
        app_label = 'core'


class ApplicationMembership(models.Model):
    """
    Members of a private image can view & launch its respective machines. If the
    can_modify flag is set, then members also have ownership--they can make
    changes. The unique_together field ensures just one of those states is true.
    """
    application = models.ForeignKey(Application)
    group = models.ForeignKey('Group')
    can_edit = models.BooleanField(default=False)

    class Meta:
        db_table = 'application_membership'
        app_label = 'core'
        unique_together = ('application', 'group')


def get_application(identifier, app_uuid=None):
    if not app_uuid:
        app_uuid = uuid5(settings.ATMOSPHERE_NAMESPACE_UUID, str(identifier))
        app_uuid = str(app_uuid)
    try:
        app = Application.objects.get(uuid=app_uuid)
        return app
    except Application.DoesNotExist:
        return None
    except Exception, e:
        logger.error(e)
        logger.error(type(e))


def create_application(identifier, provider_id, name=None,
        owner=None, version=None, description=None, tags=None,
        uuid=None):
    from core.models import AtmosphereUser
    if not uuid:
        uuid = uuid5(settings.ATMOSPHERE_NAMESPACE_UUID, str(identifier))
        uuid = str(uuid)
    if not name:
        name = "UnknownApp %s" % identifier
    if not description:
        description = "New application - %s" % name
    if not owner:
        owner = _get_admin_owner(provider_id)
    if not tags:
        tags = []
    new_app = Application.objects.create(
            name=name,
            description=description,
            created_by=owner.created_by,
            created_by_identity=owner,
            uuid=uuid)
    if tags:
        updateTags(new_app, tags, owner.created_by)
    return new_app


