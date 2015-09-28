from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils import timezone

from core.query import only_current_provider
from threepio import logger


class AtmosphereUser(AbstractUser):
    selected_identity = models.ForeignKey('Identity', blank=True, null=True)

    def group_ids(self):
        return self.group_set.values_list('id', flat=True)

    def provider_ids(self):
        return self.identity_set.values_list('provider', flat=True)

    def user_quota(self):
        identity = self.select_identity()
        identity_member = identity.identity_memberships.all()[0]
        return identity_member.quota

    @property
    def current_identities(self):
        from core.models import Identity
        all_identities = Identity.objects.none()
        for group in self.group_set.all():
            all_identities |= group.current_identities.all()
        return all_identities

    def select_identity(self):
        """
        Set, save and return an active selected_identity for the user.
        """
        # Return previously selected identity
        if self.selected_identity and self.selected_identity.is_active(self):
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

    class Meta:
        db_table = 'atmosphere_user'
        app_label = 'core'

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
                raise "No Identities on Provider %s for %s" % (default_provider,username)
            #Passing
            default_identity = default_identity[0]
            logger.debug(
                "default_identity set to %s " %
                default_identity)
            return default_identity
    except Exception as e:
        logger.exception(e)
        return None
