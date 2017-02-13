import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.core import validators
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils import timezone
from core.plugins import ValidationPluginManager, ExpirationPluginManager
from core.exceptions import InvalidUser
from threepio import logger
from django.utils.translation import ugettext_lazy as _


class AtmosphereUser(AbstractBaseUser, PermissionsMixin):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    selected_identity = models.ForeignKey('Identity', blank=True, null=True)
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

    def is_admin(self):
        if self.is_superuser or self.is_staff:
            return True
        return False

    def group_ids(self):
        return self.group_set.values_list('id', flat=True)

    def provider_ids(self):
        return self.identity_set.values_list('provider', flat=True)

    def user_quota(self):
        identity = self.select_identity()
        return identity.quota

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
    def current_providers(self):
        from core.models import Provider
        all_providers = Provider.objects.none()
        for group in self.group_set.all():
            all_providers |= Provider.objects.filter(id__in=group.current_identities.values_list('provider', flat=True))
        return all_providers

    @property
    def current_identities(self):
        from core.models import Identity
        all_identities = Identity.objects.none()
        for group in self.group_set.all():
            all_identities |= group.current_identities.all()
        return all_identities

    @classmethod
    def for_allocation_source(cls, allocation_source_id):
        from core.models import UserAllocationSource
        user_ids = UserAllocationSource.objects.filter(allocation_source__source_id=allocation_source_id).values_list('user',flat=True)
        return AtmosphereUser.objects.filter(id__in=user_ids)

    def can_use_identity(self, identity_id):
        return self.current_identities.filter(id=identity_id).count() > 0

    def select_identity(self):
        """
        Set, save and return an active selected_identity for the user.
        """
        # Return previously selected identity
        if settings.AUTO_CREATE_NEW_ACCOUNTS:
            new_identities = create_new_accounts(self.username)
        if self.selected_identity and self.selected_identity.is_active(user=self):
            return self.selected_identity
        else:
            self.selected_identity = get_default_identity(self.username)
            if self.selected_identity:
                self.save()
                return self.selected_identity

        from core.models import IdentityMembership

        for group in self.group_set.all():
            membership = IdentityMembership.get_membership_for(group.name)
            if not membership:
                continue
            self.selected_identity = membership.identity
            if self.selected_identity and self.selected_identity.is_active():
                logger.debug("Selected Identity:%s" % self.selected_identity)
                self.save()
                return self.selected_identity

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
    prof = UserProfile.objects.get_or_create(user=instance)
    if prof[1] is True:
        logger.debug("Creating User Profile for %s" % instance)

# Instantiate the hooks:
post_save.connect(get_or_create_user_profile, sender=AtmosphereUser)

# USER METHODS HERE


def get_default_provider(username):
    """
    Return default provider given
    """
    try:
        from core.models.group import get_user_group
        from core.models.provider import Provider
        group = get_user_group(username)
        provider_ids = group.current_identities.values_list(
            'provider',
            flat=True)
        provider = Provider.objects.filter(
            id__in=provider_ids,
            type__name="OpenStack")
        if provider:
            logger.debug("get_default_provider selected a new "
                         "Provider for %s: %s" % (username, provider))
            provider = provider[0]
        else:
            logger.error("get_default_provider could not find a new "
                         "Provider for %s" % (username,))
            return None
        return provider
    except Exception as e:
        logger.exception("get_default_provider encountered an error "
                         "for %s" % (username,))
        return None


def get_default_identity(username, provider=None):
    """
    Return the default identity given to the user-group for provider.
    """
    try:
        from core.models.group import get_user_group
        group = get_user_group(username)
        if not group or not group.current_identities.all().count():
            if settings.AUTO_CREATE_NEW_ACCOUNTS:
                new_identities = create_new_accounts(username, selected_provider=provider)
                if not new_identities:
                    logger.error("%s has no identities. Functionality will be severely limited." % username)
                    return None
                return new_identities[0]
            else:
                return None
        identities = group.current_identities.all()
        if provider:
            if provider.is_active():
                identities = identities.filter(provider=provider)
                return identities[0]
            else:
                logger.error("Provider provided for "
                             "get_default_identity is inactive.")
                raise "Inactive Provider provided for get_default_identity "
        else:
            default_provider = get_default_provider(username)
            default_identity = group.current_identities.filter(
                provider=default_provider)
            if not default_identity:
                logger.error("User %s has no identities on Provider %s" % (username, default_provider))
                raise Exception("No Identities on Provider %s for %s" % (default_provider, username))
            #Passing
            default_identity = default_identity[0]
            logger.debug(
                "default_identity set to %s " %
                default_identity)
            return default_identity
    except Exception as e:
        logger.exception(e)
        return None

def create_new_accounts(username, selected_provider=None):
    user = AtmosphereUser.objects.get(username=username)
    if not user.is_valid():
        raise InvalidUser("The account %s is not yet valid." % username)

    providers = get_available_providers()
    identities = []
    if not providers:
        logger.error("No currently active providers")
        return identities
    if selected_provider and selected_provider not in providers:
        logger.error("The provider %s is NOT in the list of currently active providers. Account will not be created" % selected_provider)
        return identities
    for provider in providers:
        new_identity = create_new_account_for(provider, user)
        if new_identity:
            identities.append(new_identity)
    return identities

def create_new_account_for(provider, user):
    from service.driver import get_account_driver
    existing_user_list = provider.identity_set.values_list('created_by__username', flat=True)
    if user.username in existing_user_list:
        logger.info("Accounts already exists on %s for %s" % (provider.location, user.username))
        return None
    try:
        accounts = get_account_driver(provider)
        logger.info("Create NEW account for %s" % user.username)
        new_identity = accounts.create_account(user.username)
        return new_identity
    except:
        logger.exception("Could *NOT* Create NEW account for %s" % user.username)
        return None

def get_available_providers():
    from core.models.provider import Provider
    from core.query import only_current
    available_providers = Provider.objects.filter(only_current(), public=True, active=True).order_by('id')
    return available_providers
