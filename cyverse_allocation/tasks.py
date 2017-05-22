import logging
from django.utils import timezone
from celery.decorators import task

from business_rules import run_all
from core.models.allocation_source import (
    AllocationSourceSnapshot,
    AllocationSource, UserAllocationSnapshot
)
from core.models import EventTable
from core.models.allocation_source import total_usage
from cyverse_allocation.cyverse_rules_engine_setup import CyverseTestRenewalVariables, CyverseTestRenewalActions, \
    cyverse_rules

logger = logging.getLogger(__name__)

@task(name="update_snapshot_cyverse")
def update_snapshot_cyverse(start_date=None, end_date=None):
    end_date = timezone.now().replace(microsecond=0) if not end_date else end_date

    for allocation_source in AllocationSource.objects.all():
        # calculate and save snapshots here
        allocation_source_name = allocation_source.name
        last_renewal_event = EventTable.objects.filter(
            name='allocation_source_created_or_renewed',
            payload__allocation_source_name__exact=str(allocation_source_name)).order_by('timestamp')

        if not last_renewal_event:
            logger.info('Allocation Source %s Create/Renewal event missing',allocation_source_name)
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
                                                                    'burn_rate': total_burn_rate})

        run_all(rule_list=cyverse_rules,
                defined_variables=CyverseTestRenewalVariables(allocation_source, end_date, start_date),
                defined_actions=CyverseTestRenewalActions(allocation_source, end_date), )
