from django.db import models
from django.db.models import Q
from django.utils import timezone
from uuid import uuid5, UUID
from hashlib import md5

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

    def get_scores(self):
        (ups, downs, total) = ApplicationScore.get_scores(self)
        return {"up": ups,
                "down": downs, 
                "total": total}

    def icon_url(self):
        return self.icon.url if self.icon else None

    def hash_uuid(self):
        """
        MD5 hash for icons
        """
        return md5(self.uuid).hexdigest()

    def get_provider_machines(self):
        pms = self.providermachine_set.all()
        return [{
            "start_date":pm.start_date,
            "end_date":pm.end_date,
            "alias":pm.identifier,
            "version":pm.version,
            "provider":pm.provider.id} for pm in pms]

    def save(self, *args, **kwargs):
        """
        TODO:
        When an application changes from public to private,
        or makes a change to the access_list,
        update the applicable images/provider_machines
        """
        super(Application, self).save(*args, **kwargs)
        #TODO: if changes were made..
        #self.update_images()

    def update_images():
        from service.accounts.openstack import AccountDriver as OSAccounts
        for pm in self.providermachine_set.all():
            if pm.provider.get_type_name().lower() != 'openstack':
                continue
            image_id = pm.identifier
            provider = pm.provider
            try:
                accounts = OSAccounts(pm.provider)
                image = accounts.image_manager.get_image(image_id)
                self.diff_updates(pm, image)
                accounts.image_manager.update_image(image, **updates)
            except Exception as ex:
                logger.warn("Image Update Failed for %s on Provider %s"
                            % (image_id, provider))

    def diff_updates(self, provider_machine, image):
        pass


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

    def __unicode__(self):
        return "%s %s %s" %\
            (self.group.name,
             "can edit" if self.can_edit else "can view",
             self.application.name)

    class Meta:
        db_table = 'application_membership'
        app_label = 'core'
        unique_together = ('application', 'group')

def public_applications():
    apps = []
    for app in Application.objects.filter(
            Q(end_date=None) | Q(end_date__gt=timezone.now()),
            private=False):
        if any(pm.provider.is_active()
               for pm in 
               app.providermachine_set.filter(
                   Q(end_date=None) | Q(end_date__gt=timezone.now()))):
            _add_app(apps, app)
    return apps

def visible_applications(user):
    apps = []
    if not user:
        return apps
    from core.models import Provider, ProviderMachineMembership
    active_providers = Provider.get_active()
    now_time = timezone.now()
    #Look only for 'Active' private applications
    for app in Application.objects.filter(
            Q(end_date=None) | Q(end_date__gt=now_time),
            private=True):
        #Retrieve the machines associated with this app
        machine_set = app.providermachine_set.filter(
                   Q(end_date=None) | Q(end_date__gt=now_time))
        #Skip app if all their machines are on inactive providers.
        if all(not pm.provider.is_active() for pm in machine_set):
            continue
        #Add the application if 'user' is a member of the application or PM
        if app.members.filter(user=user):
            _add_app(apps, app)
        for pm in machine_set:
            if pm.members.filter(user=user):
                _add_app(apps, app)
                break
    return apps

def _add_app(app_list, app):
    if app not in app_list:
        app_list.append(app)

    

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
        owner=None, private=False, version=None, description=None, tags=None,
        uuid=None):
    from core.models import AtmosphereUser
    if not uuid:
        uuid = uuid5(settings.ATMOSPHERE_NAMESPACE_UUID, str(identifier))
        uuid = str(uuid)
    exists = Application.objects.filter(uuid=uuid)
    if exists:
        return exists[0]
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

class ApplicationScore(models.Model):
    """
    Users can Cast their "Score" -1/0/+1 on a specific Application.
    -1 = Vote Down
     0 = Vote Removed
    +1 = Vote Up
    """
    application = models.ForeignKey(Application, related_name="scores")
    score = models.IntegerField(default=0)
    user = models.ForeignKey('AtmosphereUser')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)

    def get_vote_name(self):
        if self.score > 0:
            return "Up"
        elif self.score < 0:
            return "Down"
        else:
            return ""

    class Meta:
        db_table = 'application_score'
        app_label = 'core'

    @classmethod
    def last_vote(cls, application, user):
        votes_cast = ApplicationScore.objects.filter(
                Q(end_date=None) | Q(end_date__gt=timezone.now()),
                application=application, user=user)
        return votes_cast[0] if votes_cast else None

    @classmethod
    def get_scores(cls, application):
        scores = ApplicationScore.objects.filter(
                Q(end_date=None) | Q(end_date__gt=timezone.now()),
                application=application)
        ups = downs = 0
        for app_score in scores:
            if app_score.score > 0:
                ups += 1
            elif app_score.score < 0:
                downs += 1
        total = len(scores)
        return (ups, downs, total)

    @classmethod
    def downvote(cls, application, user):
        prev_vote = cls.last_vote(application, user)
        if prev_vote:
            prev_vote.end_date = timezone.now()
            prev_vote.save()
        return ApplicationScore.objects.create(
                application=application,
                user=user,
                score=-1)

    @classmethod
    def novote(cls, application, user):
        prev_vote = cls.last_vote(application, user)
        if prev_vote:
            prev_vote.end_date = timezone.now()
            prev_vote.save()
        return ApplicationScore.objects.create(
                application=application,
                user=user,
                score=0)

    @classmethod
    def upvote(cls, application, user):
        prev_vote = cls.last_vote(application, user)
        if prev_vote:
            prev_vote.end_date = timezone.now()
            prev_vote.save()
        return ApplicationScore.objects.create(
                application=application,
                user=user,
                score=1)

