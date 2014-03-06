from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.utils import timezone

from threepio import logger


class AtmosphereUser(AbstractUser):
    selected_identity = models.ForeignKey('Identity', blank=True, null=True)

    def user_quota(self):
        identity = self.select_identity()
        identity_member = identity.identitymembership_set.all()[0]
        return identity_member.quota

    def select_identity(self):
        """
        Set, save and return an active selected_identity for the user.
        """
        #Return previously selected identity
        if self.selected_identity and self.selected_identity.is_active():
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

    def email_hash(self):
        m = md5()
        m.update(self.user.email)
        return m.hexdigest()

    class Meta:
        db_table = 'atmosphere_user'
        app_label = 'core'


def get_default_provider(username):
    """
    Return default provider given 
    """
    try:
        from core.models.group import get_user_group
        group = get_user_group(username)
        provider = group.providers.filter(
            Q(end_date=None) | Q(end_date__gt=timezone.now()),
            active=True, type__name="OpenStack")
        if provider:
            provider = provider[0]
        else:
            logger.error("get_default_provider could not find "
                         "a valid Provider")
            return None
        logger.debug(
            "default provider is %s " % provider)
        return provider
    except IndexError:
        logger.info("No provider found for %s" % username)
        return None
    except Exception, e:
        logger.exception(e)
        return None


def get_default_identity(username, provider=None):
    """
    Return the default identity given to the user-group for provider.
    """
    try:
        from core.models.group import get_user_group
        group = get_user_group(username)
        identities = group.identities.all()
        if provider:
            if provider.is_active():
                identities = identities.filter(provider=provider)
                return identities[0]
            else:
                logger.error("Provider provided for "
                             "get_default_identity is inactive.")
                raise("Provider provided for get_default_identity "
                      "is inactive.")
        else:
            default_provider = get_default_provider(username)
            default_identity = group.identities.filter(
                provider=default_provider)[0]
            logger.debug(
                "default_identity set to %s " %
                default_identity)
            return default_identity
    except Exception, e:
        logger.exception(e)
        return None
