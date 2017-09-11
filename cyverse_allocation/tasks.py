import pprint

from business_rules import run_all
from celery.decorators import task
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import datetime
from threepio import celery_logger as logger

from core.models import EventTable
from core.models.allocation_source import AllocationSourceSnapshot, AllocationSource, UserAllocationSnapshot, \
    total_usage
from cyverse_allocation.cyverse_rules_engine_setup import CyverseTestRenewalVariables, CyverseTestRenewalActions, \
    cyverse_rules, renewal_strategies


@task(name="update_snapshot_cyverse")
def update_snapshot_cyverse(start_date=None, end_date=None):
    logger.debug("update_snapshot_cyverse task started at %s." % datetime.now())
    end_date = timezone.now().replace(microsecond=0) if not end_date else end_date

    for allocation_source in AllocationSource.objects.order_by('name'):
        # calculate and save snapshots here
        allocation_source_name = allocation_source.name
        last_renewal_event = EventTable.objects.filter(
            name='allocation_source_created_or_renewed',
            payload__allocation_source_name__exact=str(allocation_source_name)).order_by('timestamp')

        if not last_renewal_event:
            logger.info('Allocation Source %s Create/Renewal event missing', allocation_source_name)
            continue

        start_date = last_renewal_event.last().timestamp.replace(microsecond=0) if not start_date else start_date

        total_compute_used = 0
        total_burn_rate = 0
        for user in allocation_source.all_users:
            compute_used, burn_rate = total_usage(user.username, start_date=start_date,
                                                  end_date=end_date, allocation_source_name=allocation_source_name,
                                                  burn_rate=True)

            UserAllocationSnapshot.objects.update_or_create(allocation_source=allocation_source, user=user,
                                                            defaults={'compute_used': compute_used,
                                                                      'burn_rate': burn_rate})
            total_compute_used += compute_used
            total_burn_rate += burn_rate
        AllocationSourceSnapshot.objects.update_or_create(allocation_source=allocation_source,
                                                          defaults={'compute_used': total_compute_used,
                                                                    'global_burn_rate': total_burn_rate})

        run_all(rule_list=cyverse_rules,
                defined_variables=CyverseTestRenewalVariables(allocation_source, end_date, start_date),
                defined_actions=CyverseTestRenewalActions(allocation_source, end_date), )
    # At the end of the task, fire-off an allocation threshold check
    logger.debug("update_snapshot_cyverse task finished at %s." % datetime.now())
    allocation_threshold_check.apply_async()


@task(name="allocation_threshold_check")
def allocation_threshold_check():
    logger.debug("allocation_threshold_check task started at %s." % datetime.now())
    if not settings.CHECK_THRESHOLD:
        logger.debug("CHECK_THRESHOLD is FALSE -- allocation_threshold_check task finished at %s." % datetime.now())
        return

    for allocation_source in AllocationSource.objects.filter(compute_allowed__gte=0).all():
        snapshot = allocation_source.snapshot
        percentage_used = (snapshot.compute_used / snapshot.compute_allowed) * 100
        # check if percentage more than threshold
        THRESHOLD = [50.0, 90.0]
        for threshold in THRESHOLD:
            if percentage_used > threshold:
                compute_used = snapshot.compute_used
                allocation_source_name = allocation_source.name

                # check if event has been fired
                prev_event = EventTable.objects.filter(name='allocation_source_threshold_met',
                                                       payload__allocation_source_name=allocation_source_name,
                                                       payload__threshold=threshold).last()
                if prev_event:
                    continue

                payload = {}
                payload['allocation_source_name'] = allocation_source_name
                payload['threshold'] = threshold
                payload['usage_percentage'] = float(percentage_used)

                EventTable.objects.create(
                    name='allocation_source_threshold_met',
                    payload=payload,
                    entity_id=payload['allocation_source_name'])
                break
    logger.debug("allocation_threshold_check task finished at %s." % datetime.now())


# Renew all allocation sources or a specific renewal strategy without waiting for rules engine
def renew_allocation_sources(renewal_strategy=False, current_time=False, ignore_current_compute_allowed=False,
                             dry_run=False):
    current_time = timezone.now() if not current_time else current_time

    for strategy, args in renewal_strategies.iteritems():

        if renewal_strategy and (str(renewal_strategy) != str(strategy)):
            continue
        compute_allowed = args['compute_allowed']
        for allocation_source in AllocationSource.objects.filter(renewal_strategy=str(strategy)):
            renew_allocation_source_for(compute_allowed, allocation_source, current_time,
                                        ignore_current_compute_allowed, dry_run)


def renew_allocation_source_for(compute_allowed, allocation_source, current_time, ignore_current_compute_allowed=False,
                                dry_run=False):
    # carryover logic
    # remaining_compute = 0 if source_snapshot.compute_allowed - source_snapshot.compute_used < 0 else source_snapshot.compute_allowed - source_snapshot.compute_used
    # total_compute_allowed = float(remaining_compute + compute_allowed)

    total_compute_allowed = compute_allowed
    if not ignore_current_compute_allowed:
        source_snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=allocation_source).last()
        if source_snapshot:
            snapshot_compute_allowed = float(source_snapshot.compute_allowed)
            if snapshot_compute_allowed > compute_allowed:
                total_compute_allowed = snapshot_compute_allowed

    # fire renewal event

    renewal_strategy = allocation_source.renewal_strategy
    allocation_source_name = allocation_source.name
    allocation_source_uuid = allocation_source.uuid

    payload = {
        "uuid": str(allocation_source_uuid),
        "renewal_strategy": renewal_strategy,
        "allocation_source_name": allocation_source_name,
        "compute_allowed": total_compute_allowed
    }

    if dry_run:
        dry_run_text = '''EventTable.objects.create(name='allocation_source_created_or_renewed',
                              payload={},
                              entity_id='{}',
                              timestamp={})
        '''.format(pprint.pformat(payload), allocation_source_name, current_time)
        print(dry_run_text)
    else:
        EventTable.objects.create(name='allocation_source_created_or_renewed',
                                  payload=payload,
                                  entity_id=allocation_source_name,
                                  timestamp=current_time)
