from django.contrib.auth.models import User as DjangoUser

from django.db.models.signals import post_save
from django.db import models

from threepio import logger
from atmosphere import settings

from core.ldap import get_uid_number
from core.models.group import getUsergroup
from core.models.identity import Identity


class UserProfile(models.Model):
    user = models.OneToOneField(DjangoUser, primary_key=True)
    #Backend Profile attributes
    send_emails = models.BooleanField(default=True)
    quick_launch = models.BooleanField(default=True)
    vnc_resolution = models.CharField(max_length=255, default='800x600')
    #Frontend profile attributes
    default_size = models.CharField(max_length=255, default='m1.small')
    background = models.CharField(max_length=255, default='default')
    icon_set = models.CharField(max_length=255, default='default')
    selected_identity = models.ForeignKey(Identity, blank=True, null=True)

    def user_quota(self):
        identity = getDefaultIdentity(self.user.username)
        identity_member = identity.identitymembership_set.all()[0]
        return identity_member.quota

    class Meta:
        db_table = 'user_profile'
        app_label = 'core'


#Connects a user profile to created accounts
def get_or_create_user_profile(sender, instance, created, **kwargs):
    #logger.debug("Get or Creating Profile for %s" % instance)
    prof = UserProfile.objects.get_or_create(user=instance)[0]
    if not prof.selected_identity:
        available_identities = instance.identity_set.all()
        logger.info("No selected identity. Has:%s" % available_identities)
        if available_identities:
                prof.selected_identity = available_identities[0]
                prof.save()

post_save.connect(get_or_create_user_profile, sender=DjangoUser)


def getDefaultProvider(username):
    """
    return the Default provider given to the user-group
    """
    profile = UserProfile.objects.get(user__username=username)
    if profile.selected_provider:
        return profile.selected_provider
    else:
        try:
            group = getUsergroup(username)
            profile.selected_provider = group.providers.get(
                location="EUCALYPTUS")
            profile.save()
            logger.debug(
                "profile.selected_provider set to %s " %
                profile.selected_provider)
            return profile.selected_provider
        except IndexError:
            logger.info("No provider found for %s" % username)
            return None
        except Exception, e:
            logger.exception(e)
            return None


def getDefaultIdentity(username, provider=None):
    """
    return the Default identity given to the user-group for provider
    """
    profile = UserProfile.objects.get(user__username=username)
    if profile.selected_identity:
        return profile.selected_identity
    else:
        try:
            group = getUsergroup(username)
            identities = group.identities.all()
            if provider:
                identities = identities.filter(provider=provider)
                return identities[0]
            else:
                default_identity = group.identities.filter(
                    provider__location="EUCALYPTUS")[0]
                profile.selected_identity = default_identity
                profile.save()
                logger.debug(
                    "profile.selected_identity set to %s " %
                    profile.selected_identity)
                return profile.selected_identity
        except Exception, e:
            logger.exception(e)
            return None


def get_ranges(uid_number, inc=0):
    """
    Return two block ranges to be used to create subnets for
    Atmosphere users.

    NOTE: If you change MAX_SUBNET then you should likely change
    the related math.
    """
    MAX_SUBNET = 4064  # Note 
    n = uid_number % MAX_SUBNET

    #16-31
    block1 = (n + inc) % 16 + 16

    #1-254
    block2 = ((n + inc) / 16) % 254 + 1
    
    return (block1, block2)

def get_default_subnet(username, inc=0):
    """
    Return the default subnet for the username and provider.

    Add and mod by inc to allow for collitions.
    """
    uid_number = get_uid_number(username)

    if uid_number:
        (block1, block2) = get_ranges(uid_number, inc)
    else:
        (block1, block2) = get_ranges(0, inc)

    if username == "jmatt":
        return "172.16.42.0/24"  # /flex
    else:
        return "172.%s.%s.0/24" % (block1, block2)
