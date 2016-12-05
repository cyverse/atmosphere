from uuid import uuid4, uuid5
from hashlib import md5

from django.db import models
from django.db.models import Q
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from threepio import logger

from atmosphere import settings

from core import query
from core.models.provider import Provider, AccountProvider
from core.models.identity import Identity
from core.models.tag import Tag, updateTags
from core.models.application_version import ApplicationVersion

import json

class Application(models.Model):

    """
    An application is a collection of ApplicationVersions.
    Each version can contain one or many providermachines.
    Each ApplicationVersion represents a single revision of the Application made by the creator,
    together forming a linear history of how the application progressed.

    Note: The created_by field here is used for logging only;
    do not rely on it for permissions; use ApplicationMembership instead.
    """
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    name = models.CharField(max_length=256)
    # TODO: Dynamic location for upload_to
    icon = models.ImageField(upload_to="applications", null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    private = models.BooleanField(default=False)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    # User/Identity that created the application object
    created_by = models.ForeignKey('AtmosphereUser')
    created_by_identity = models.ForeignKey(Identity, null=True)

    @property
    def all_versions(self):
        version_set = ApplicationVersion.objects.filter(
            application=self)
        return version_set

    @property
    def all_machines(self):
        from core.models import ProviderMachine
        providermachine_set = ProviderMachine.objects.filter(
            application_version__application=self)
        return providermachine_set

    @property
    def full_description(self):
        description = self.description
        for version in self.active_versions():
            description += version.change_log

    def end_date_all(self, now=None):
        if not now:
            now = timezone.now()
        for version in self.versions.all():
            version.end_date_all(now)
        if not self.end_date:
            self.end_date = now
            self.save()

    def active_versions(self, now_time=None):
        return self.versions.filter(
            query.only_current(now_time)).order_by('start_date')

    def get_icon_url(self):
        return self.icon.url if self.icon else None

    @property
    def latest_version(self):
        try:
            return self.active_versions().last()
        except ApplicationVersion.DoesNotExist:
            return None

    def is_owner(self, atmo_user):
        return self.created_by == atmo_user

    def change_owner(self, identity, user=None, propagate=True):
        if not user:
            user = identity.created_by
        self.created_by = user
        self.created_by_identity = identity
        self.save()
        if propagate:
           [v.change_owner(identity, user, propagate=propagate) for v in self.versions.all()]

    @classmethod
    def public_apps(cls):
        public_images = Application.objects.filter(
            query.only_current_apps(), private=False)
        return public_images

    @classmethod
    def shared_with(cls, user):
        group_ids = user.group_ids()
        shared_images = Application.objects.filter(
            query.only_current_apps(),
            (Q(versions__machines__members__id__in=group_ids) |
             Q(versions__membership__id__in=group_ids))
        )
        return shared_images

    @classmethod
    def admin_apps(cls, user):
        """
        Just give staff the ability to launch everything that isn't end-dated.
        """
        provider_ids = user.provider_ids()
        admin_images = Application.objects.filter(
            query.only_current(),
            versions__machines__instance_source__provider__id__in=provider_ids)
        return admin_images

    @classmethod
    def images_for_user(cls, user=None):
        from core.models.user import AtmosphereUser
        is_public = Q(private=False)
        if not user or isinstance(user, AnonymousUser):
            # Images that are not endated and are public
            return Application.objects.filter(query.only_current_apps() & is_public).distinct()
        if not isinstance(user, AtmosphereUser):
            raise Exception("Expected user to be of type AtmosphereUser"
                            " - Received %s" % type(user))
        queryset = None
        if user.is_staff:
            # Any image on a provider in the staff's provider list
            queryset = Application.objects.filter(query.in_users_providers(user))
        else:
            # This query is not the most clear. Here's an explanation:
            # Include all images created by the user or active images in the
            # users providers that are either shared with the user or public
            queryset = Application.objects.filter(
                    query.created_by_user(user) |
                    (query.only_current_apps() &
                     query.in_users_providers(user) &
                     (query.images_shared_with_user(user) | is_public)))
        return queryset.distinct()

    def get_metrics(self):
        """
        Aggregate 'all-version' metrics
        More specific metrics can be found at the version level
        """
        versions = self.versions.all()
        version_map = {}
        all_count = 0
        all_total = timezone.timedelta(0)
        all_avg = timezone.timedelta(0)
        all_user_domain_map = {}
        for version in versions:
            version_metrics = version.get_metrics()
            provider_metrics = version_metrics['providers']
            for key,val in version_metrics['domains'].items():
                count = all_user_domain_map.get(key,0)
                count += val
                all_user_domain_map[key] = count
            all_avg += sum([prov['avg_time'] for prov in provider_metrics.values()], timezone.timedelta(0))
            all_total += sum([prov['total'] for prov in provider_metrics.values()], timezone.timedelta(0))
            all_count += sum([prov['count'] for prov in provider_metrics.values()])
            version_map[version.name] = version_metrics
        return {'versions': {
            'avg_time': all_avg, 'total': all_total,
            'count': all_count,'domains':all_user_domain_map
            }
        }

    def _current_machines(self, request_user=None):
        """
        Return a list of current provider machines.
        NOTE: Defined as:
                * Provider is still listed as active
                * Provider has not exceeded its end_date
                * The ProviderMachine has not exceeded its end_date
        """
        providermachine_set = self.all_machines
        pms = providermachine_set.filter(
            query.only_current_source(),
            instance_source__provider__active=True)
        if request_user:
            if isinstance(request_user, AnonymousUser):
                providers = Provider.objects.filter(public=True)
            else:
                providers = [identity.provider for identity in
                             request_user.identity_set.all()]
            pms = pms.filter(instance_source__provider__in=providers)
        return pms

    def first_machine(self):
        # Out of all non-end dated machines in this application
        providermachine_set = self.all_machines
        first = providermachine_set.filter(
            query.only_current_source()
            ).order_by('instance_source__start_date').first()
        return first

    def last_machine(self):
        providermachine_set = self.all_machines
        # Out of all non-end dated machines in this application
        last = providermachine_set.filter(
            query.only_current_source()
            ).order_by('instance_source__start_date').last()
        return last

    def get_projects(self, user):
        projects = self.projects.filter(
            query.only_current(),
            owner=user)
        return projects

    def update_images(self, **updates):
        for pm in self._current_machines():
            pm.update_image(**updates)

    def update_owners(self, owners_list):
        """
        Update the list of people allowed to view the image
        """
        pass

    def update_privacy(self, is_private):
        """
        Applications deal with 'private' as being true,
        NOTE: Images commonly use the 'is_public' field,
        so the value must be flipped internally.
        """
        is_public = not is_private
        self.update_images(visibility='public' if is_public else 'private')
        self.private = is_private
        self.save()

    def featured(self):
        return True if self.tags.filter(name__iexact='featured') else False

    def is_bookmarked(self, request_user):
        from core.models import AtmosphereUser
        if isinstance(request_user, str):
            request_user = AtmosphereUser.objects.get(username=request_user)
        if isinstance(request_user, AnonymousUser):
            return False
        user_bookmarks = [bookmark.application for bookmark
                          in request_user.bookmarks.all()]
        return self in user_bookmarks

    def get_members(self):
        members = list(self.applicationmembership_set.all())
        for provider_machine in self._current_machines():
            members.extend(
                provider_machine.providermachinemembership_set.all())
        return members

    def get_scores(self):
        (ups, downs, total) = ApplicationScore.get_scores(self)
        return {"up": ups, "down": downs, "total": total}

    def icon_url(self):
        return self.icon.url if self.icon else None

    def hash_uuid(self):
        """
        MD5 hash for icons
        """
        return md5(self.uuid).hexdigest()

    def get_provider_machines(self):
        pms = self._current_machines()
        return [pm.to_dict() for pm in pms]

    def save(self, *args, **kwargs):
        """
        TODO:
        When an application changes from public to private,
        or makes a change to the access_list,
        update the applicable images/provider_machines
        """
        super(Application, self).save(*args, **kwargs)
        # TODO: if changes were made..
        # TODO: Call out to OpenStack, Admin(Email), Groupy Hooks..

    def update(self, *args, **kwargs):
        """
        Allows for partial updating of the model
        """
        # Upload args into kwargs
        for arg in args:
            for (key, value) in arg.items():
                kwargs[key] = value
        # Update the values
        for key in kwargs.keys():
            if key == 'tags':
                if not isinstance(kwargs[key], list):
                    tags_list = kwargs[key].split(",")
                else:
                    tags_list = kwargs[key]
                updateTags(self, tags_list)
                continue
            setattr(self, key, kwargs[key])
        self.save()
        return self

    def __unicode__(self):
        return "%s by %s - %s" \
            % (self.name, self.created_by,
               self.start_date if not self.end_date else 'END-DATED')

    class Meta:
        db_table = 'application'
        app_label = 'core'


class ApplicationMembership(models.Model):

    """
    Members of a private image can view & launch its respective machines. If
    the can_modify flag is set, then members also have ownership--they can make
    changes. The unique_together field ensures just one of those states is
    true.
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


def _get_app_by_name(provider_uuid, name):
    """
    Retrieve app by name

    """
    try:
        app = Application.objects.get(
            versions__machines__instance_source__provider__uuid=provider_uuid,
            name=name)
        return app
    except Application.DoesNotExist:
        return None
    except Application.MultipleObjectsReturned:
        logger.warn(
            "Possible Application Conflict: Multiple applications named:"
            "%s. Check this query for more details" % name)
        return None


def _get_app_by_identifier(provider_uuid, identifier):
    """
    Retrieve app by 'instance_source.identifier'
    This will retrieve the 'correct' app if a NEW application is choosen
    that does NOT match the UUID hash of the provider_machine
    """
    try:
        # Attempt #1: to retrieve application based on identifier
        app = Application.objects.get(
            versions__machines__instance_source__provider__uuid=provider_uuid,
            versions__machines__instance_source__identifier=identifier)
        return app
    except Application.DoesNotExist:
        return None


def get_application(provider_uuid, identifier, app_name, app_uuid=None):
    application = _get_app_by_identifier(provider_uuid, identifier)
    if application:
        return application
    application = _get_app_by_name(provider_uuid, app_name)
    if application:
        return application
    return _get_app_by_uuid(identifier, app_uuid)


def _generate_app_uuid(identifier):
    app_uuid = uuid5(
        settings.ATMOSPHERE_NAMESPACE_UUID,
        str(identifier))
    return str(app_uuid)


def verify_app_uuid(app_uuid, identifier):
    valid_uuid = _generate_app_uuid(identifier)
    return valid_uuid == app_uuid

def _get_app_by_uuid(identifier, app_uuid):
    """
    Last-ditch placement effort. Hash the identifier and use that as the lookup
    """
    if not app_uuid:
        app_uuid = _generate_app_uuid(identifier)
    app_uuid = str(app_uuid)
    try:
        app = Application.objects.get(
            uuid=app_uuid)
        return app
    except Application.DoesNotExist:
        return None
    except Exception as e:
        logger.exception(e)


def _username_lookup(provider_uuid, username):
    try:
        return Identity.objects.get(
            provider__uuid=provider_uuid,
            created_by__username=username)
    except Identity.DoesNotExist:
        return None


def update_application(application, new_name=None, new_tags=None,
                       new_description=None):
    """
    This is a dumb way of doing things. Fix this.
    """
    if new_name:
        application.name = new_name
    if new_description:
        application.description = new_description
    if new_tags:
        application.tags = new_tags
    application.save()
    return application


def create_application(
        provider_uuid,
        identifier,
        name=None,
        created_by_identity=None,
        created_by=None,
        description=None,
        private=False,
        tags=None,
        uuid=None):
    """
    Create application & Initial ApplicationVersion.
    Build information (Based on MachineRequest or API inputs..)
    and RETURN Application!!
    """
    new_app = None

    if not uuid:
        uuid = _generate_app_uuid(identifier)

    existing_app = Application.objects.filter(uuid=uuid)
    if existing_app.count():
        new_app = existing_app[0]

    if not name:
        name = "Imported App: %s" % identifier
    if not description:
        description = "Imported Application - %s" % name
    if created_by:
        created_by_identity = _username_lookup(
            provider_uuid,
            created_by.username)
    if not created_by_identity:
        created_by_identity = _get_admin_owner(provider_uuid)
    if not tags:
        tags = []
    elif isinstance(tags, basestring):
        if "[" in tags:
            #Format expected -- ["CentOS", "development", "test1"]
            tags = json.loads(tags)
        elif "," in tags:
            #Format expected -- CentOS, development, test1,test2,test3
            tags = [t.strip() for t in tags.split(',')]
        else:
            tags = [tags]
    if new_app:
        new_app.name = name
        new_app.description = description
        new_app.created_by = created_by_identity.created_by
        new_app.created_by_identity = created_by_identity
        new_app.private = private
        new_app.save()
    else:
        new_app = Application.objects.create(
            name=name,
            description=description,
            created_by=created_by_identity.created_by,
            created_by_identity=created_by_identity,
            private=private,
            uuid=uuid)
    if tags:
        updateTags(new_app, tags, created_by_identity.created_by)
    return new_app

#FIXME: This class marked for removal
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
        return ApplicationScore.objects.create(application=application,
                                               user=user,
                                               score=-1)

    @classmethod
    def novote(cls, application, user):
        prev_vote = cls.last_vote(application, user)
        if prev_vote:
            prev_vote.end_date = timezone.now()
            prev_vote.save()
        return ApplicationScore.objects.create(application=application,
                                               user=user,
                                               score=0)

    @classmethod
    def upvote(cls, application, user):
        prev_vote = cls.last_vote(application, user)
        if prev_vote:
            prev_vote.end_date = timezone.now()
            prev_vote.save()
        return ApplicationScore.objects.create(application=application,
                                               user=user,
                                               score=1)


class ApplicationBookmark(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    user = models.ForeignKey('AtmosphereUser', related_name="bookmarks")
    application = models.ForeignKey(Application, related_name="bookmarks")

    def __unicode__(self):
        return "%s + %s" % (self.user, self.application)

    class Meta:
        db_table = 'application_bookmark'
        app_label = 'core'


class ApplicationThreshold(models.Model):
    """
    The Application Threshold represents the minimum CPU/Memory
    required to launch the VM. (This is optional)
    """
    application_version = models.OneToOneField(
        ApplicationVersion,
        related_name="threshold",
        blank=True,
        null=True)
    memory_min = models.IntegerField(default=0)
    cpu_min = models.IntegerField(default=0)

    def __unicode__(self):
        return "%s requires >%s MB memory, >%s CPU" % (self.application_version,
                                                           self.memory_min,
                                                           self.cpu_min)

    class Meta:
        db_table = 'application_threshold'
        app_label = 'core'


# NOTE: Should it always take the first admin?
def _get_admin_owner(provider_uuid):
    admins = AccountProvider.objects.filter(provider__uuid=provider_uuid)

    # If an admin exists return its identity
    if admins.count() > 0:
        return admins.first().identity

    logger.warn("AccountProvider could not be found for provider %s."
                " AccountProviders are necessary to claim ownership "
                " for identities that do not yet exist in the DB."
                % Provider.objects.get(uuid=provider_uuid))
    return None
