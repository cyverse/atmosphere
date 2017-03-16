from core.models.instance_source import InstanceSource
from django.utils import timezone
from core.models.instance import Instance
from core.models.instance_history import InstanceStatusHistory, InstanceStatus
from core.models.allocation_source import AllocationSource
from core.models.size import Size
from core.models.event_table import EventTable
from core.models.identity import Identity
from core.models.provider import Provider, ProviderType, PlatformType
from api.tests.factories import UserFactory
import uuid


class UserWorkflow:

    def __init__(self):

        self.user = UserFactory.create()
        provider_type = ProviderType(name='Test_%s'%self.user.username)
        provider_type.save()
        platform_type = PlatformType(name='test-platform-%s'%self.user.username)
        platform_type.save()
        provider = Provider(location='BIO5', type=provider_type, virtualization=platform_type)
        provider.save()

        active_status = InstanceStatus.objects.filter(name='active').last()
        if not active_status:
            active_status = InstanceStatus(name='active')
            active_status.save()

        suspended_status = InstanceStatus.objects.filter(name='suspended').last()
        if not suspended_status:
            suspended_status = InstanceStatus(name='suspended')
            suspended_status.save()

        self.provider = provider
        self.active_status = active_status
        self.suspended_status = suspended_status

    def create_instance(self, start_date=None):
        if not start_date:
            start_date = timezone.now()

        provider_alias = str(uuid.uuid4())

        identity = Identity.objects.filter(created_by=self.user).last()
        if not identity:
            identity = Identity(created_by=self.user, provider=self.provider)
            identity.save()

        instance_source = InstanceSource(provider=self.provider, identifier=str(uuid.uuid4()), created_by=self.user,
                                         created_by_identity=identity)
        instance_source.save()

        instance = Instance(source=instance_source, provider_alias=provider_alias,
                            created_by=self.user, start_date=start_date)
        instance.save()

        self.create_instance_status_history(instance,start_date=start_date,status='active')

        return instance

    def assign_allocation_source_to_user(self, allocation_source, timestamp=None):
        if not timestamp:
            timestamp = timezone.now()

        # Spoof UserAllocationSource

        new_user_allocation_source = {
            'source_id': allocation_source.source_id,
            'username': self.user.username
        }

        user_allocation_source_event = EventTable.objects.create(name='user_allocation_source_assigned',
                                                                 payload=new_user_allocation_source,
                                                                 entity_id=new_user_allocation_source['username'],
                                                                 timestamp=timestamp)

    def assign_allocation_source_to_instance(self, allocation_source, instance, timestamp=None):

        if not timestamp:
            timestamp = timezone.now()

        # Associate Instance with Allocation Source

        if self.user!= instance.created_by:
            raise Exception('instance %s does not belong to user %s'%(instance,self.user.username))

        payload = {
            "allocation_source_id": allocation_source.source_id,
            "instance_id": instance.provider_alias
        }

        instance_allocation_event = EventTable.objects.create(name='instance_allocation_source_changed',
                                                              payload=payload,
                                                              entity_id=self.user.username,
                                                              timestamp=timestamp)

    def create_instance_status_history(self, instance, start_date=None, status=None ,cpu=None, end_date=None):
        # Spoof InstanceStatusHistory

        if self.user!= instance.created_by:
            raise Exception('instance %s does not belong to user %s'%(instance,self.user.username))

        if not start_date:
            start_date=timezone.now()
        if not cpu:
            cpu = 1

        if status == 'active' or not status:
            current_status = self.active_status
        else:
            current_status = self.suspended_status
        size = Size(alias=uuid.uuid4(), name='small', provider=self.provider, cpu=cpu, disk=1, root=1, mem=1)
        size.save()

        # find last instance history and end date it

        last_instance_history = InstanceStatusHistory.objects.filter(instance=instance).order_by('start_date').last()
        if last_instance_history:
            last_instance_history.end_date = start_date
            last_instance_history.save()

        instance_history1 = InstanceStatusHistory(
            instance=instance, size=size, status=current_status, start_date=start_date,
            end_date=end_date)
        instance_history1.save()

    def is_allocation_source_assigned_to_user(self):
        query = EventTable.objects.filter(name='user_allocation_source_assigned', entity_id=self.user.username)
        return True if query else False


def create_allocation_source(name, compute_allowed,renewal_strategy=None, timestamp=None):
    if not timestamp:
        timestamp = timezone.now()

    # Spoof Allocation Source creation

    if not renewal_strategy:
        renewal_strategy='default'

    new_allocation_source = {
        'source_id': str(uuid.uuid4()),
        'name': name,
        'compute_allowed': compute_allowed,
        'renewal_strategy': renewal_strategy
    }

    EventTable.objects.create(name='allocation_source_created',
                                                        payload=new_allocation_source,
                                                        entity_id=new_allocation_source['source_id'],
                                                        timestamp=timestamp)

    return AllocationSource.objects.filter(name=name).last()


def change_renewal_strategy(allocation_source, renewal_strategy, timestamp=None):
    if not timestamp:
        timestamp = timezone.now()

    # Spoof Renewal Strategy change

    if not renewal_strategy:
        raise('Please provide a renewal strategy to change to')

    renewal_strategy_change_payload = {
        "source_id": str(allocation_source.source_id),
        "renewal_strategy": renewal_strategy
    }

    EventTable.objects.create(name='allocation_source_renewal_strategy_changed',
                              payload = renewal_strategy_change_payload,
                              entity_id = renewal_strategy_change_payload['source_id'],
                              timestamp = timestamp)

