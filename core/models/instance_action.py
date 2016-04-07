"""
  Instance action model for atmosphere.
"""
import uuid
from django.db import models

from core.models.managers import InstanceActionsManager
from core.models import Instance

from threepio import logger


class InstanceAction(models.Model):
    """
    An InstanceAction is a 'Type' field that lists every available action for
    a given instance on a 'generic' cloud.
    see 'ProviderInstanceAction' to Enable/disable a
    specific instance action on a given cloud(Provider)
    """
    key = models.CharField(max_length=256, unique=True, editable=False)
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True, null=True)

    # Model Managers
    objects = models.Manager()  # The default manager.
    valid_actions = InstanceActionsManager()

    @classmethod
    def _retrieve_instance(cls, instance_id):
        """
        Fixme: Likely this is already covered by core.models.instance
        Figure out how to 'smooth things over' without circular dependencies
        between Instance --> InstanceAction --> Instance
        """
        instance_kwargs = {}
        if type(instance_id) == int:
            instance_kwargs['id'] = instance_id
        elif type(instance_id) in [str, unicode, basestring, uuid.UUID]:
            instance_kwargs['provider_alias'] = instance_id
        try:
            inst = Instance.objects.get(**instance_kwargs)
            return inst
        except Instance.DoesNotExist:
            logger.info("Asking for actions on non-existent instance: %s "
                        % instance_id)
            return None

    @classmethod
    def filter_by_instance(cls, instance, queryset=None):
        if not queryset:
            queryset = cls.objects.all()

        if not isinstance(instance, Instance):
            instance = cls._retrieve_instance(instance)
        # Filter down to what the *provider* will let you do to the *instance*
        valid_actions = cls.filter_by_provider(
            instance.source.provider.id, queryset)
        # THEN Filter down to what the *instance* will let you do
        valid_actions = cls.valid_instance_actions(instance, valid_actions)
        return valid_actions

    @classmethod
    def filter_by_provider(cls, provider_id, queryset=None):
        # TODO: Filter actions down to those available for a specific provider
        if not queryset:
            queryset = cls.objects.all()
        kwargs = {
            'provider_actions__enabled': True
            }
        if type(provider_id) == int:
            kwargs['provider_actions__provider__id'] = provider_id
        elif type(provider_id) in [str, uuid.UUID]:
            kwargs['provider_actions__provider__uuid'] = provider_id
        return queryset.filter(**kwargs)

    @classmethod
    def valid_instance_actions(cls, instance, queryset=None):
        """
        Giiven an instance, determine the appropriate actions available via API
        """
        last_history = instance.get_last_history()
        last_status = last_history.status.name
        last_activity = last_history.activity
        all_actions = []
        # Basic Actions: Reboot and terminate will work in (almost) every case.
        all_actions.append('Terminate')
        all_actions.append('Reboot')
        all_actions.append('Hard Reboot')
        if last_status == 'active':
            all_actions.append('Redeploy')
            # If we are "in the process of deploying"
            # Our actions are limited to Redeploy + <Basic Actions>
            if not last_activity:
                # "Green-light" active has access to all remaining actions.
                all_actions.append('Resize')
                all_actions.append('Shelve')
                all_actions.append('Suspend')
                all_actions.append('Stop')
                all_actions.append('Terminate')
                all_actions.append('Imaging')
        elif last_status == "suspended":
            # Suspended instances can be resumed + <Basic Actions>
            all_actions.append('Resume')
        elif last_status == "shutoff":
            # Suspended instances can be started + <Basic Actions>
            all_actions.append('Start')
        elif last_status == "shelved":
            # Shelved instances can be unshelved or offloaded + <Basic Actions>
            all_actions.append('Shelve Offload')
            all_actions.append('Unshelve')

        if len(all_actions) == 2:
            logger.debug(
                "Edge case Warning: Status/activity=(%s/%s) returns "
                "no updates to actions" % (last_status, last_activity))

        if not queryset:
            queryset = cls.objects.all()
        return queryset.filter(key__in=all_actions)

    def __unicode__(self):
        return "%s (%s)" %\
            (self.name, self.key)
