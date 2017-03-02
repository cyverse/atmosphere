import json
import uuid
from behave import *
from datetime import timedelta
from dateutil.parser import parse
from dateutil.rrule import rrule, HOURLY
from django.utils import timezone
from django.test.client import Client
from django.core.urlresolvers import reverse
from rest_framework.test import APIClient
from core.models.allocation_source import total_usage
from business_rules import run_all
from cyverse_allocation.cyverse_rules_engine_setup import CyverseTestRenewalVariables, CyverseTestRenewalActions,cyverse_rules
from core.models import (
    AllocationSourceSnapshot, AllocationSource, Instance, Size,
    ProviderMachine, InstanceStatusHistory, AtmosphereUser)
from api.tests.factories import (
     InstanceFactory, InstanceHistoryFactory, InstanceStatusFactory,
    ProviderMachineFactory, IdentityFactory, ProviderFactory)

######## Story Implementation ##########

@given('one admin user and two regular users who can launch instances')
def step_impl(context):
    context.client = Client()
    user, not_created = AtmosphereUser.objects.get_or_create(username='lenards', password='lenards')
    if not_created:
        user.is_staff = True
        user.is_superuser = True
        user.save()
    context.admin_user = user
    context.client.login()

    user_1 = AtmosphereUser.objects.get_or_create(username='amitj', password='amitj')
    context.user_1 = user_1[0]
    user_2 = AtmosphereUser.objects.get_or_create(username='julianp', password='julianp')
    context.user_2 = user_2[0]

@when('admin creates allocation source')
def step_impl(context):
    for row in context.table:
        response = context.client.post('/api/v2/allocation_sources',
                                               {"renewal_strategy": row['renewal strategy'],
                                                "name": row['name'],
                                                "compute_allowed": row['compute allowed']})
        context.uuid = response.data['uuid']
        context.renewal_strategy = row['renewal strategy']
        assert response.status_code==201


@when('Users added to allocation source launch instance (at the same time)')
def step_impl(context):
    user = [context.user_1,context.user_2]
    count = 0
    time_created = timezone.now()
    context.time_user_launched_instance = time_created
    for row in context.table:
        # add user to allocation source
        context.client.post('/api/v2/user_allocation_sources',
                            {"username": user[count].username,
                             "source_id": context.uuid})
        provider_alias = launch_instance(user[count],time_created,int(row["cpu"]))
        # Add instance to allocation source
        context.client.post('/api/v2/instance_allocation_source',
                            {"instance_id": provider_alias,
                             "source_id": context.uuid
                             })
        time_stopped = time_created + timedelta(days=int(row["days_instance_is_active"]))
        stop_instance(user,provider_alias,time_stopped)
        count+=1


@then('after days = {no_of_days} Allocation source used = {compute_used} and remaining compute = {compute_remaining}')
def step_impl(context, no_of_days, compute_used, compute_remaining):
    #find how often renewal is fired for this strategy
    current_time = timezone.now()
    allocation_source = AllocationSource.objects.filter(uuid=context.uuid).last()
    start_date = current_time
    end_date = current_time+timedelta(days=int(no_of_days))
    celery_iterator = list(rrule(HOURLY, interval=12, dtstart=start_date, until=end_date))

    prev_time = ''

    for current_time in celery_iterator:
        # update AllocationSourceSnapshot with the current compute_used
        if not prev_time:
            prev_time = current_time
        else:
            snapshot = AllocationSourceSnapshot.objects.filter(allocation_source=allocation_source).last()
            snapshot.compute_used = float(snapshot.compute_used) + get_compute_used(allocation_source,current_time,prev_time)
            snapshot.save()

            run_all(rule_list=cyverse_rules,
                    defined_variables=CyverseTestRenewalVariables(allocation_source, current_time),
                    defined_actions=CyverseTestRenewalActions(allocation_source, current_time),
                    )
            prev_time=current_time

    #find compute_used
    compute_used_total = 0
    for user in allocation_source.all_users:
        compute_used_total += total_usage(user.username,start_date=context.time_user_launched_instance,end_date=end_date,allocation_source_name=allocation_source.name)
    #find compute_remaining
    compute_allowed = AllocationSourceSnapshot.objects.filter(allocation_source=allocation_source).last().compute_allowed
    compute_used_from_snapshot = AllocationSourceSnapshot.objects.filter(
        allocation_source=allocation_source).last().compute_used
    assert int(compute_used) == compute_used_total
    assert (float(compute_allowed)-float(compute_used_from_snapshot))==float(compute_remaining)

########### Helpers ###############

def launch_instance(user,time_created,cpu):
    # context.user is admin and regular user
    provider = ProviderFactory.create()
    from core.models import IdentityMembership, Identity
    user_group = IdentityMembership.objects.filter(member__name=user.username)
    if not user_group:
        user_identity = IdentityFactory.create_identity(
            created_by=user,
            provider=provider)
    else:
        user_identity = Identity.objects.all().last()
    admin_identity = user_identity

    provider_machine = ProviderMachine.objects.all()
    if not provider_machine:
        machine = ProviderMachineFactory.create_provider_machine(user, user_identity)
    else:
        machine = ProviderMachine.objects.all().last()

    active_instance = InstanceFactory.create(
    name="Instance in active",
    provider_alias=uuid.uuid4(),
    source=machine.instance_source,
    created_by=user,
    created_by_identity=user_identity,
    start_date=timezone.now())

    active = InstanceStatusFactory.create(name='active')
    size = Size(alias=uuid.uuid4(), name='small', provider=provider, cpu=cpu, disk=1, root=1, mem=1)
    size.save()
    InstanceHistoryFactory.create(
        status=active,
        activity="",
        instance=active_instance,
        start_date = time_created,
        size=size
    )

    return active_instance.provider_alias


def stop_instance(user,provider_alias,time_stopped):

    active_instance = Instance.objects.filter(provider_alias=provider_alias).last()

    size = Size.objects.all().last()

    status_history = InstanceStatusHistory.objects.filter(instance=active_instance).last()
    status_history.end_date = time_stopped
    status_history.save()

    suspended = InstanceStatusFactory.create(name='suspended')
    InstanceHistoryFactory.create(
        status=suspended,
        activity="",
        instance=active_instance,
        start_date = time_stopped,
        size=size
    )

def get_compute_used(allocation_source,current_time,prev_time):

    compute_used = 0
    for user in allocation_source.all_users:
        compute_used += total_usage(user.username, start_date=prev_time,
                    end_date=current_time, allocation_source_name=allocation_source.name)

    return compute_used

