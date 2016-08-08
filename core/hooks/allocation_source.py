from core.models import (
    AllocationSource, Instance, AtmosphereUser,
    UserAllocationBurnRateSnapshot,
    InstanceAllocationSourceSnapshot,
    AllocationSourceSnapshot)

# Save hooks
def listen_for_allocation_snapshot_changes(sender, instance, created, **kwargs):
    """
    This listener expects:
    EventType - 'allocation_source_snapshot'
    EventPayload - {
        "allocation_source_id": "37623",
        "compute_used":100.00,  # 100 hours used ( a number, not a string!)
        "global_burn_rate":2.00,  # 2 hours used each hour
    }
    The method should result in an up-to-date snapshot of AllocationSource usage.
    """
    event = instance
    if event.name != 'allocation_source_snapshot':
        return None

    payload = event.payload
    allocation_source_id = payload['allocation_source_id']
    compute_used = payload['compute_used']
    global_burn_rate = payload['global_burn_rate']

    allocation_source = AllocationSource.objects.filter(source_id=allocation_source_id).first()
    if not allocation_source:
        return None
    try:
        snapshot = AllocationSourceSnapshot.objects.get(
            allocation_source=allocation_source
        )
        snapshot.compute_used = compute_used
        snapshot.global_burn_rate = global_burn_rate
        snapshot.save()
    except AllocationSourceSnapshot.DoesNotExist:
        snapshot = AllocationSourceSnapshot.objects.create(
            allocation_source=allocation_source,
            compute_used=compute_used,
            global_burn_rate=global_burn_rate
        )
    return snapshot


def listen_for_user_burn_rate_changes(sender, instance, created, **kwargs):
    """
    This listener expects:
    EventType - 'user_burn_rate_changed'
    EventPayload - {
        "allocation_source_id": "37623",
        "username":"sgregory",
        "burn_rate": 3.00 # 3 hours used each hour
    }

    The method should result in an up-to-date burn rate snapshot for the specific User+AllocationSource
    """
    event = instance
    if event.name != 'user_burn_rate_changed':
        return None

    payload = event.payload
    allocation_source_id = payload['allocation_source_id']
    burn_rate = payload['burn_rate']
    username = payload['username']

    allocation_source = AllocationSource.objects.filter(source_id=allocation_source_id).first()
    if not allocation_source:
        return None
    user = AtmosphereUser.objects.filter(username=username).first()
    if not user:
        return None

    try:
        snapshot = UserAllocationBurnRateSnapshot.objects.get(
                allocation_source=allocation_source,
                user=user,
            )
        snapshot.burn_rate = burn_rate
        snapshot.save()
    except UserAllocationBurnRateSnapshot.DoesNotExist:
        snapshot = UserAllocationBurnRateSnapshot.objects.create(
                allocation_source=allocation_source,
                user=user,
                burn_rate=burn_rate
            )
    return snapshot


def listen_for_instance_allocation_changes(sender, instance, created, **kwargs):
    """
    This listener expects:
    EventType - 'instance_allocation_source_changed'
    EventPayload - {
        "allocation_source_id": "37623",
        "instance_id":"2439b15a-293a-4c11-b447-bf349f16ed2e"
    }

    The method should result in an up-to-date snapshot of Instance+AllocationSource
    """
    event = instance
    if event.name != 'instance_allocation_source_changed':
        return None

    payload = event.payload
    allocation_source_id = payload['allocation_source_id']
    instance_id = payload['instance_id']

    allocation_source = AllocationSource.objects.filter(source_id=allocation_source_id).first()
    if not allocation_source:
        return None
    instance = Instance.objects.filter(provider_alias=instance_id).first()
    if not instance:
        return None

    try:
        snapshot = InstanceAllocationSourceSnapshot.objects.get(
            instance=instance)
        snapshot.allocation_source = allocation_source
        snapshot.save()
    except InstanceAllocationSourceSnapshot.DoesNotExist:
        snapshot = InstanceAllocationSourceSnapshot.objects.create(
            allocation_source=allocation_source,
            instance=instance)
    return snapshot


