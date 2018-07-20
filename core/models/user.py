import uuid
from hashlib import md5

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.core import validators
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils import timezone
from core.plugins import ValidationPluginManager, ExpirationPluginManager, DefaultQuotaPluginManager, AccountCreationPluginManager
from core.query import only_current
from core.exceptions import InvalidUser
from threepio import logger
from django.utils.translation import ugettext_lazy as _


class AtmosphereUser(AbstractBaseUser, PermissionsMixin):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    end_date = models.DateTimeField(null=True, blank=True)
    # Ripped from django.contrib.auth.models to force a larger max_length:
    username = models.CharField(
        _('username'),
        max_length=256,
        unique=True,
        help_text=_('Required. 256 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[
            validators.RegexValidator(
                r'^[\w.@+-]+$',
                _('Enter a valid username. This value may contain only '
                  'letters, numbers ' 'and @/./+/-/_ characters.')
            ),
        ],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_('first name'), max_length=64, blank=True)
    last_name = models.CharField(_('last name'), max_length=256, blank=True)
    # These methods unchanged from 'AbstractUser'
    email = models.EmailField(_('email address'), blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'atmosphere_user'
        app_label = 'core'

    def get_profile(self):
        """
        """
        from core.models.profile import UserProfile
        return UserProfile.objects.filter(user__username=self.username).distinct().get()

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)
    # END-rip.

    @staticmethod
    def users_for_instance(instance_id, leader_only=False):
        """
        is_leader: Explicitly filter out instances if `is_leader` is True/False, if None(default) do not test for project leadership.
        """
        instance_query = Q(memberships__group__projects__instances__provider_alias=instance_id)
        if leader_only == True:
            instance_query &= Q(memberships__is_leader=True)
        return AtmosphereUser.objects.filter(instance_query).distinct()

    def is_admin(self):
        if self.is_superuser or self.is_staff:
            return True
        return False

    def all_projects(self):
        from core.models.project import Project
        p_qs = Project.objects.none()
        for group in self.group_set.all():
            p_qs |= group.projects.all()
        return p_qs

    def group_ids(self):
        return self.memberships.values_list('group__id', flat=True)

    def provider_ids(self):
        return self.identity_set.values_list('provider', flat=True)

    def is_expired(self):
        """
        Call expiration plugin to determine if user is expired
        """
        _is_expired = ExpirationPluginManager.is_expired(self)
        return _is_expired

    def is_valid(self):
        """
        Call validation plugin to determine user validity
        """
        _is_valid = ValidationPluginManager.is_valid(self)
        return _is_valid

    @property
    def is_enabled(self):
        """
        User is enabled if:
        1. They do not have an end_date
        _OR_ They have an end_date that is not past the current time
        2. The 'is_active' flag is True
        """
        now_time = timezone.now()
        return self.is_active and \
            (not self.end_date or self.end_date > now_time)

    @property
    def current_identities(self):
        from core.models import Identity
        all_identities = Identity.objects.none()
        for membership in self.memberships.select_related('group'):
            group = membership.group
            all_identities |= Identity.objects.filter(id__in=group.current_identities.values_list('id', flat=True))
        all_identities |= Identity.objects.filter(created_by=self).distinct()
        return all_identities

    @property
    def current_providers(self):
        from core.models import Provider
        all_providers = Provider.objects.none()
        for membership in self.memberships.select_related('group'):
            group = membership.group
            all_providers |= Provider.objects.filter(id__in=group.current_identities.values_list('provider', flat=True))
        all_providers |= Provider.objects.filter(cloud_admin=self)
        return all_providers

    @classmethod
    def for_allocation_source(cls, allocation_source_id):
        from core.models import UserAllocationSource
        user_ids = UserAllocationSource.objects.filter(allocation_source__source_id=allocation_source_id).values_list('user',flat=True)
        return AtmosphereUser.objects.filter(id__in=user_ids)

    def volume_set(self):
        from core.models import Volume
        volume_db_ids = [source.volume.id for source in
                         self.source_set.filter(volume__isnull=False)]
        return Volume.objects.filter(id__in=volume_db_ids)

    def email_hash(self):
        m = md5()
        m.update(self.user.email)
        return m.hexdigest()

# Save Hooks Here:


def get_or_create_user_profile(sender, instance, created, **kwargs):
    from core.models.profile import UserProfile
    try:
        prof = UserProfile.objects.filter(user=instance).distinct().get()
    except UserProfile.DoesNotExist:
        prof = UserProfile.objects.get_or_create(user=instance)
        if prof[1] is True:
            logger.debug("Creating User Profile for %s" % instance)
    return prof

# Instantiate the hooks:
post_save.connect(get_or_create_user_profile, sender=AtmosphereUser)

# USER METHODS HERE


def _get_providers(username, selected_provider=None):
    from core.models import Provider
    user = AtmosphereUser.objects.get(username=username)
    public_providers = Provider.objects.filter(only_current(), active=True, public=True)

    providers = user.current_providers.filter(only_current(), active=True)
    if not providers:
        providers = public_providers
    else:
        providers |= public_providers
    if selected_provider and providers and selected_provider not in providers:
        logger.error("The provider %s is NOT in the list of currently active providers. Account will not be created" % selected_provider)
        return (user, providers.none())

    return (user, providers)


def create_new_accounts(username, selected_provider=None):
    identities = []
    (user, providers) = _get_providers(username, selected_provider)
    for provider in providers:
        try:
            new_identities = AccountCreationPluginManager.create_accounts(provider, username)
            if new_identities:
                identities.extend(new_identities)
        except ValueError as err:
            logger.warn(err)
    return identities


def create_new_account_for(provider, user):
    from service.exceptions import AccountCreationConflict
    from service.driver import get_account_driver
    existing_user_list = provider.identity_set.values_list('created_by__username', flat=True)
    if user.username in existing_user_list:
        logger.info("Accounts already exists on %s for %s" % (provider.location, user.username))
        return None
    try:
        accounts = get_account_driver(provider)
        logger.info("Create NEW account for %s" % user.username)
        default_quota = DefaultQuotaPluginManager.default_quota(user=user, provider=provider)
        new_identity = accounts.create_account(user.username, quota=default_quota)
        return new_identity
    except AccountCreationConflict:
        raise  # TODO: Ideally, have sentry handle these events, rather than force an Unhandled 500 to bubble up.
    except:
        logger.exception("Could *NOT* Create NEW account for %s" % user.username)
        return None


def get_available_providers():
    from core.models.provider import Provider
    available_providers = Provider.objects.filter(only_current(), public=True, active=True).order_by('id')
    return available_providers
