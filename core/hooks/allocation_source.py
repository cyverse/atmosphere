import uuid

from django.conf import settings
from threepio import logger

from core.models import (
    AllocationSource, Instance, AtmosphereUser,
    UserAllocationSnapshot,
    InstanceAllocationSourceSnapshot,
    AllocationSourceSnapshot)
from core.models import UserAllocationSource
from core.models.allocation_source import get_allocation_source_object


def listen_for_allocation_overage(sender, instance, raw, **kwargs):
    """
    This listener expects:
    EventType - 'allocation_source_snapshot'
    EventPayload - {
        "allocation_source_name": "37623",
        "compute_used":100.00,  # 100 hours used ( a number, not a string, IN HOURS!)
        "global_burn_rate":2.00,  # 2 hours used each hour
    }
    The method will only run in the case where an allocation_source `compute_used` >= source.compute_allowed
    """

    event = instance
    if event.name != 'allocation_source_snapshot':
        return None
    # Circular dep...
    from core.models import EventTable
    payload = event.payload
    allocation_source_name = payload['allocation_source_name']
    new_compute_used = payload['compute_used']
    source = AllocationSource.objects.filter(name=allocation_source_name).last()
    prev_enforcement_event = EventTable.objects \
        .filter(name="allocation_source_threshold_enforced") \
        .filter(entity_id=allocation_source_name).last()
    # test for previous event of 'allocation_source_threshold_enforced'
    if prev_enforcement_event:
        return
    if new_compute_used == 0:
        return
    if not source:
        return
    if source.compute_allowed in [None, 0]:
        return
    # FIXME: Remove this line when you are ready to start enforcing 100% allocation:
    return
    current_percentage = int(100.0 * new_compute_used / source.compute_allowed) if source.compute_allowed != 0 else 0
    if new_compute_used < source.compute_allowed:
        return
    enforce_allocation_overage.apply_async(args=(source.name,))
    new_payload = {
        "allocation_source_name": source.name,
        "actual_value": current_percentage
    }
    return


def listen_before_allocation_snapshot_changes(sender, instance, raw, **kwargs):
    """
    DEV NOTE: This is a *pre_save* signal. As such, the arguments are slightly different and the object in the database matching the data will be the "before", while the data coming into the function should be considered the "after". For more details about pre_save signals: https://docs.djangoproject.com/en/dev/ref/signals/#pre-save

    This listener expects:
    EventType - 'allocation_source_snapshot'
    EventPayload - {
        "allocation_source_name": "37623",
        "compute_used":100.00,  # 100 hours used ( a number, not a string!)
        "global_burn_rate":2.00,  # 2 hours used each hour
    }
    The method should result in an up-to-date snapshot of AllocationSource usage.
    """

    event = instance
    if event.name != 'allocation_source_snapshot':
        return None
    # Circular dep...
    from core.models import EventTable

    payload = event.payload
    allocation_source_name = payload['allocation_source_name']
    new_compute_used = payload['compute_used']
    threshold_values = getattr(settings, "ALLOCATION_SOURCE_WARNINGS", [])
    source = AllocationSource.objects.filter(name=allocation_source_name).last()
    if new_compute_used == 0:
        return
    if not source:
        return
    if source.compute_allowed in [None, 0]:
        return
    prev_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=source).first()
    ##CHANGED
    # prev_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source__name=allocation_source_name).last()
    if not prev_snapshot:
        prev_compute_used = 0
    else:
        prev_compute_used = float(prev_snapshot.compute_used)
    prev_percentage = int(100.0 * prev_compute_used / source.compute_allowed)
    current_percentage = int(100.0 * new_compute_used / source.compute_allowed)
    print "Souce: %s (%s) Previous:%s - New:%s" % (
        source.name, allocation_source_name, prev_percentage, current_percentage)
    percent_event_triggered = None
    # Compare 'Now snapshot' with Previous snapshot. Have we "crossed a threshold?"
    # If yes:
    # # Check if we have already fired the `allocation_source_threshold_met` event
    # # If not:
    # # # Fire the `allocation_source_threshold_met` event
    for test_threshold in threshold_values:
        if prev_percentage < test_threshold \
                and current_percentage >= test_threshold:
            percent_event_triggered = test_threshold
    if not percent_event_triggered:
        return
    print "Email Event triggered for %s users: %s" % (source.all_users.count(), percent_event_triggered)
    prev_email_event = EventTable.objects \
        .filter(name="allocation_source_threshold_met") \
        .filter(entity_id=allocation_source_name,
                payload__threshold=percent_event_triggered)
    if prev_email_event:
        return
    new_payload = {
        "threshold": percent_event_triggered,
        "allocation_source_name": allocation_source_name,
        "actual_value": current_percentage
    }
    EventTable.create_event(
        name="allocation_source_threshold_met",
        entity_id=allocation_source_name,
        payload=new_payload)
    return


def listen_for_allocation_threshold_met(sender, instance, created, **kwargs):
    """
    This listener expects:
    EventType - 'allocation_source_threshold_met'
    EventEntityID - '<allocation_source.name>'
    EventPayload - {
        "allocation_source_name": "37623",
        "threshold":20  # The '20%' threshold was hit for this allocation.
    }
    The method should fire off emails to the users who should be informed of the new threshold value.
    """
    # FIXME+TODO: next version: Fire and respond to the `clear_allocation_threshold_met` for a given allocation_source_name (This event should be generated any time you `.save()` and update the `compute_allowed` for an AllocationSource
    event = instance
    if event.name != 'allocation_source_threshold_met':
        return None
    payload = event.payload
    allocation_source_name = payload['allocation_source_name']
    threshold = payload['threshold']
    actual_value = payload['actual_value']
    if not settings.ENFORCING:
        return None
    source = AllocationSource.objects.filter(name=allocation_source_name).last()
    ##CHANGED
    # source = AllocationSource.objects.filter(name=allocation_source_name).last()
    if not source:
        return None
    users = AtmosphereUser.for_allocation_source(source.name)

    for user in users:
        send_usage_email_to(user, source, threshold, actual_value)


def send_usage_email_to(user, source, threshold, actual_value=None):
    from core.email import send_allocation_usage_email
    user_snapshot = UserAllocationSnapshot.objects.filter(
        allocation_source=source, user=user).last()
    if not actual_value:
        actual_value = int(source.snapshot.compute_used / source.compute_allowed * 100)
    if not user_snapshot:
        compute_used = None
    else:
        compute_used = getattr(user_snapshot, 'compute_used')
    try:
        send_allocation_usage_email(
            user, source, threshold, actual_value,
            user_compute_used=compute_used)
    except Exception:
        logger.exception("Could not send a usage email to user %s" % user)


def listen_for_allocation_snapshot_changes(sender, instance, created, **kwargs):
    """
    This listener expects:
    EventType - 'allocation_source_snapshot'
    EventPayload - {
        "allocation_source_name": "37623",
        "compute_used":100.00,  # 100 hours used ( a number, not a string!)
        "global_burn_rate":2.00,  # 2 hours used each hour
    }
    The method should result in an up-to-date snapshot of AllocationSource usage.
    """
    event = instance
    if event.name != 'allocation_source_snapshot':
        return None

    payload = event.payload
    allocation_source_name = payload['allocation_source_name']
    compute_used = payload['compute_used']
    global_burn_rate = payload['global_burn_rate']

    allocation_source = AllocationSource.objects.filter(name=allocation_source_name).last()
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


def listen_for_user_snapshot_changes(sender, instance, created, **kwargs):
    """
    This listener expects:
    EventType - 'user_allocation_snapshot_changed'
    EventPayload - {
        "allocation_source_name": "37623",
        "username":"sgregory",
        "compute_used":100.00,  # 100 hours used total ( a number, not a string!)
        "burn_rate": 3.00 # 3 hours used every hour
    }

    The method should result in an up-to-date compute used + burn rate snapshot for the specific User+AllocationSource
    """
    event = instance
    if event.name != 'user_allocation_snapshot_changed':
        return None

    payload = event.payload
    allocation_source_name = payload['allocation_source_name']
    burn_rate = payload['burn_rate']
    compute_used = payload['compute_used']
    username = payload['username']

    allocation_source = AllocationSource.objects.filter(name=allocation_source_name).last()
    if not allocation_source:
        return None
    user = AtmosphereUser.objects.filter(username=username).first()
    if not user:
        return None

    try:
        snapshot = UserAllocationSnapshot.objects.get(
            allocation_source=allocation_source,
            user=user,
        )
        snapshot.burn_rate = burn_rate
        snapshot.compute_used = compute_used
        snapshot.save()
    except UserAllocationSnapshot.DoesNotExist:
        snapshot = UserAllocationSnapshot.objects.create(
            allocation_source=allocation_source,
            user=user,
            burn_rate=burn_rate,
            compute_used=compute_used
        )
    return snapshot


## EVENT FIRED WHEN USER IS REMOVED FROM AN ALLOCATION SOURCE

def listen_for_instance_allocation_changes(sender, instance, created, **kwargs):
    """
       This listener expects:
       EventType - 'instance_allocation_source_changed'
       entity_id - "amitj" # Username

       # CyVerse Payload

       EventPayload - {
           "instance_id" : "abcd-efgh-ij245-23823h",
           "allocation_source_name" : "TG-AG100345"
       }

       # Jetstream Payload

       EventPayload - {
           "instance_id" : "abcd-efgh-ij245-23823h",
           "allocation_source_name" : "TG-AG100345"
       }

       The method assigns an instance to an allocation source
    """
    event = instance
    if event.name != 'instance_allocation_source_changed':
        return None
    logger.info("Instance allocation changed event: %s" % event.__dict__)
    payload = event.payload
    assert 'allocation_source_name' in payload  # TODO: Standardize? And a schema?

    allocation_source_name = payload['allocation_source_name']
    allocation_source = AllocationSource.objects.filter(name=allocation_source_name).last()
    if not allocation_source:
        raise ("Allocation Source %s does not exist" % (payload['allocation_source_name']))

    instance_id = payload['instance_id']
    instance = Instance.objects.filter(provider_alias=instance_id).first()
    if not instance:
        # TODO: Not sure we should just swallow this either.
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


## EVENT FIRED WHEN ALLOCATION SOURCE IS CREATED OR RENEWED

def listen_for_allocation_source_created_or_renewed(sender, instance, created, **kwargs):
    """
       This listener expects:
       EventType - 'allocation_source_created_or_renewed'
       entity_id - "TG-AG100345" # Allocation Source Name

       # CyVerse Payload

       EventPayload - {
           "uuid" : "16fd2706-8baf-433b-82eb-8c7fada847da"
           "allocation_source_name": "TG-AG100345",
           "compute_allowed":1000,
           "renewal_strategy":"default"
       }

       # Jetstream Payload

       EventPayload - {
           "allocation_source_name": "TG-AG100345",
           "compute_allowed":1000,
       }

       The method should result in renewal of allocation source
    """
    event = instance
    if event.name != 'allocation_source_created_or_renewed':
        return None
    logger.info("Allocation Source created or renewed event: %s" % event.__dict__)
    payload = event.payload
    allocation_source_name = payload['allocation_source_name']
    compute_allowed = payload['compute_allowed']

    if 'renewal_strategy' in payload:
        object_updated, created = AllocationSource.objects.update_or_create(
            uuid=uuid.UUID(payload['uuid']),
            name=allocation_source_name,
            defaults={'compute_allowed': compute_allowed,
                      'renewal_strategy': payload['renewal_strategy']}
        )

        allocation_source = get_allocation_source_object(payload['uuid'])

        AllocationSourceSnapshot.objects.update_or_create(
            allocation_source=allocation_source,
            defaults={"compute_allowed": compute_allowed,
                      "global_burn_rate": 0,
                      "compute_used": 0.0,
                      "updated": event.timestamp})

    else:
        # Jetstream
        object_updated, created = AllocationSource.objects.update_or_create(
            name=allocation_source_name,
            defaults={'compute_allowed': compute_allowed}
        )

    logger.info('object_updated: %s, created: %s' % (object_updated, created,))


## EVENT FIRED WHEN COMPUTE ALLOWED FOR AN ALLOCATION SOURCE IS UPDATED

def listen_for_allocation_source_compute_allowed_changed(sender, instance, created, **kwargs):
    """
           This listener expects:
           EventType - 'allocation_source_compute_allowed_changed'
           entity_id - "TG-AG100345" # Allocation Source Name

           # CyVerse Payload

           EventPayload - {
               "allocation_source_name" : "TG-amit100568",
               "compute_allowed":1000
           }

           # Jetstream Payload

           EventPayload - {
               "allocation_source_name": "TG-AG100345",
               "compute_allowed":1000,
           }

           The method should result in an updated compute allowed
        """
    event = instance
    if event.name != 'allocation_source_compute_allowed_changed':
        return None
    logger.info("Allocation Source Compute Allowed Changed event: %s" % event.__dict__)
    payload = event.payload
    assert 'allocation_source_name' in payload  # TODO: Standardize? And a schema?
    allocation_source_name = payload['allocation_source_name']
    source = AllocationSource.objects.filter(name=allocation_source_name).last()

    compute_allowed = payload['compute_allowed']
    source.compute_allowed = compute_allowed
    source.save()


## EVENT FIRED WHEN USER IS ASSIGNED TO AN ALLOCATION SOURCE

def listen_for_user_allocation_source_created(sender, instance, created, **kwargs):
    """
           This listener expects:
           EventType - 'user_allocation_source_created'
           entity_id - "amitj" # Username

           # CyVerse Payload

           EventPayload - {
               "allocation_source_name" : "TG-amit100568",
           }

           # Jetstream Payload

           EventPayload - {
               "allocation_source_name": "TG-AG100345",
           }

           The method should assign a user to an allocation source
        """
    event = instance
    from core.models import EventTable, AtmosphereUser, AllocationSource
    assert isinstance(event, EventTable)
    if event.name != 'user_allocation_source_created':
        return None
    logger.info('user_allocation_source_created: %s' % event.__dict__)
    payload = event.payload
    allocation_source_name = payload['allocation_source_name']
    user_name = event.entity_id

    object_updated, created = UserAllocationSource.objects.update_or_create(
        user=AtmosphereUser.objects.get_by_natural_key(user_name),
        allocation_source=AllocationSource.objects.get(name=allocation_source_name)
    )
    logger.info('object_updated: %s, created: %s' % (object_updated, created,))


## EVENT FIRED WHEN USER IS REMOVED FROM AN ALLOCATION SOURCE

def listen_for_user_allocation_source_deleted(sender, instance, created, **kwargs):
    """
          This listener expects:
          EventType - 'user_allocation_source_deleted'
          entity_id - "amitj" # Username

          # CyVerse Payload

          EventPayload - {
              "allocation_source_name" : "TG-amit100568",
          }

          # Jetstream Payload

          EventPayload - {
              "allocation_source_name": "TG-AG100345",
          }

          The method should remove a user from an allocation source
       """

    event = instance
    from core.models import EventTable

    assert isinstance(event, EventTable)
    if event.name != 'user_allocation_source_deleted':
        return None
    logger.info('user_allocation_source_deleted: %s' % event.__dict__)
    payload = event.payload
    allocation_source_name = payload['allocation_source_name']
    user_name = event.entity_id

    deleted_info = UserAllocationSource.objects.filter(
        user__username__exact=user_name,
        allocation_source__name__exact=allocation_source_name).delete()
    logger.info('deleted_info: {}'.format(deleted_info))


# THIS EVENT IS NEVER FIRED

def listen_for_instance_allocation_removed(sender, instance, created, **kwargs):
    """
    This listener expects:
    EventType - 'instance_allocation_source_removed'
    EventPayload - {
        "allocation_source_id": "TG-amit100568",
        "instance_id":"2439b15a-293a-4c11-b447-bf349f16ed2e"
    """
    event = instance
    if event.name != 'instance_allocation_source_removed':
        return None
    logger.info("Instance allocation removed event: %s" % event.__dict__)
    payload = event.payload
    allocation_source_id = payload['allocation_source_id']
    instance_id = payload['instance_id']
    allocation_source = AllocationSource.objects.filter(source_id=allocation_source_id).first()
    if not allocation_source:
        return None
    instance = Instance.objects.filter(provider_alias=instance_id).first()
    if not instance:
        return None
    snapshot = InstanceAllocationSourceSnapshot.objects.get(
        instance=instance, allocation_source=allocation_source)
    snapshot.delete()


## EVENT FIRED WHEN RENEWAL STRATEGY OF ALLOCATION SOURCE IS CHANGED

def listen_for_allocation_source_renewal_strategy_changed(sender, instance, created, **kwargs):
    """
        #CyVerse Payload

        This listener expects:
               EventType - 'allocation_source_renewal_strategy_changed'
               entity_id - "TG-amit100568" #Allocation Source Name

               EventPayload - {
                   "renewal_strategy": "workshop",
               }

               The method should result in renewal strategy of allocation source being changed

    """
    event = instance
    if event.name != 'allocation_source_renewal_strategy_changed':
        return None
    logger.info('Allocation Source renewal strategy changed event: %s', event.__dict__)
    payload = event.payload
    allocation_source_name = payload['allocation_source_name']
    new_renewal_strategy = payload['renewal_strategy']
    try:
        AllocationSource.objects.update_or_create(name=allocation_source_name,
                                                  defaults={'renewal_strategy': new_renewal_strategy})
    except Exception as e:
        raise Exception(
            'Allocation Source %s renewal strategy could not be changed because of the following error %s' % (
                allocation_source_name, e))
    return


# THIS EVENT IS NEVER FIRED

def listen_for_allocation_source_name_changed(sender, instance, created, **kwargs):
    """
        This listener expects:
               EventType - 'allocation_source_name_changed'
               EventPayload - {
                   "source_id": "32712",
                   "name": "TestAllocationSource2",
               }

               The method should result in name of allocation source being changed

    """
    event = instance
    if event.name != 'allocation_source_name_changed':
        return None
    logger.info('Allocation Source name changed event: %s', event.__dict__)
    payload = event.payload
    allocation_source_id = payload['source_id']
    new_name = payload['name']
    ##CHANGED
    # allocation_source = AllocationSource.objects.filter(source_id=allocation_source_id)
    try:
        allocation_source = get_allocation_source_object(allocation_source_id)
        allocation_source.name = new_name
        allocation_source.save()

    except Exception as e:
        raise Exception('Allocation Source %s name could not be changed because of the following error %s' % (
            allocation_source.name, e))
    return

## EVENT FIRED WHEN ALLOCATION SOURCE IS CHANGED

def listen_for_allocation_source_removed(sender, instance, created, **kwargs):
    """
         # CyVerse Payload
         This listener expects:
                   EventType -'allocation_source_removed'
                   entity_id - "TestAllocationSource2" # Allocation Source Name
                   EventPayload - {
                       "allocation_source_name": "TestAllocationSource2",
                       "delete_date": "2016-05-16T00:00T00:00"
                   }

                   The method should result in removal of allocation source
    """
    event = instance
    if event.name != 'allocation_source_removed':
        return None
    logger.info('Allocation Source deleted event: %s', event.__dict__)
    payload = event.payload

    allocation_source = AllocationSource.objects.filter(name=payload['allocation_source_name']).last()
    allocation_source.end_date = payload['delete_date']
    allocation_source.save()

    return
