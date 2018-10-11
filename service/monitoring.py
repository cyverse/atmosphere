import random
import time
from django.core.exceptions import ObjectDoesNotExist
import pytz
from django.db.models import Q
from django.utils import timezone
from threepio import logger
from core.models import AccountProvider
from core.models.credential import Credential
from core.models import InstanceStatusHistory
from core.models.instance import Instance as CoreInstance
from core.models.instance import (
    convert_esh_instance, _esh_instance_size_to_core
)
from service.cache import get_cached_instances, get_cached_driver
from service.instance import suspend_instance, stop_instance, destroy_instance, shelve_instance, offload_instance
from django.conf import settings
from rtwo.exceptions import LibcloudInvalidCredsError


# Private
def _include_all_idents(identities, owner_map):
    # Include all identities with 0 instances to the monitoring
    identity_owners = [
        ident.get_credential('ex_tenant_name') for ident in identities
    ]
    owners_w_instances = owner_map.keys()
    for user in identity_owners:
        if user not in owners_w_instances:
            owner_map[user] = []
    return owner_map


def _make_instance_owner_map(instances, users=None):
    owner_map = {}

    for i in instances:
        if users and i.owner not in users:
            continue
        key = i.owner
        instance_list = owner_map.get(key, [])
        instance_list.append(i)
        owner_map[key] = instance_list
    return owner_map


def _core_instances_for(identity, start_date=None):
    if not start_date:
        # Can't use 'None' as a query value
        start_date = timezone.datetime(1970, 1, 1).replace(tzinfo=pytz.utc)
    return CoreInstance.objects.filter(
        Q(instancestatushistory__end_date=None) |
        Q(instancestatushistory__end_date__gt=start_date) | Q(end_date=None) |
        Q(end_date__gt=start_date),
    # NOTE: May need to remove this created_by line
    # down-the-road as we share user/tenants.
        created_by=identity.created_by,
        created_by_identity=identity
    ).distinct()


def _select_identities(provider, users=None):
    if users:
        return provider.identity_set.filter(created_by__username__in=users)
    return provider.identity_set.all()


def _convert_tenant_id_to_names(instances, tenants):
    for i in instances:
        for tenant in tenants:
            if type(tenant) == dict:
                if tenant['id'] == i.owner:
                    i.owner = tenant['name']
            else:
                if tenant.id == i.owner:
                    i.owner = tenant.name
    return instances


def _get_identity_from_tenant_name(provider, username):
    # FIXME: This needs to be `username, tenant_name` because the `project_name` no longer has to match the `username`
    try:
        # NOTE: I could see this being a problem when 'user1' and 'user2' use
        # TODO: Ideally we would be able to extract some more information
        #      when we move away from explicit user-groups.
        credential = Credential.objects.get(
            Q(key='ex_project_name'),
            value=username,
            identity__provider=provider
        )
        identity = credential.identity
        return identity
    except Credential.MultipleObjectsReturned:
        logger.warn(
            "%s has >1 Credentials on Provider %s" % (username, provider)
        )
        credential = Credential.objects.filter(
            key='ex_project_name', value=username, identity__provider=provider
        )[0]
        identity = credential.identity
        return identity
    except Credential.DoesNotExist:
        return None


def _execute_provider_action(identity, user, instance, action_name):
    driver = get_cached_driver(identity=identity)

    # NOTE: This if statement is a HACK! It will be removed when IP management is enabled in an upcoming version. -SG
    reclaim_ip = True if identity.provider.location != 'iPlant Cloud - Tucson' else False
    # ENDNOTE

    # NOTE: This metadata statement is a HACK! It should be removed when all instances matching this metadata key have been removed.
    instance_has_home_mount = instance.extra['metadata'].get(
        'atmosphere_ephemeral_home_mount', 'false'
    ).lower()
    if instance_has_home_mount == 'true' and action_name == 'Shelve':
        logger.info(
            "Instance %s will be suspended instead of shelved, because the ephemeral storage is in /home"
            % instance.id
        )
        action_name = 'Suspend'

    logger.info(
        "User %s has gone over their allocation on Instance %s - Enforcement Choice: %s"
        % (user, instance, action_name)
    )
    try:
        if not action_name:
            logger.debug("No 'action_name' provided")
            return
        elif action_name == 'Suspend':
            suspend_instance(
                driver, instance, identity.provider.uuid, identity.uuid, user,
                reclaim_ip
            )
        elif action_name == 'Stop':
            stop_instance(
                driver, instance, identity.provider.uuid, identity.uuid, user,
                reclaim_ip
            )
        elif action_name == 'Shelve':
            shelve_instance(
                driver, instance, identity.provider.uuid, identity.uuid, user,
                reclaim_ip
            )
        elif action_name == 'Shelve Offload':
            offload_instance(
                driver, instance, identity.provider.uuid, identity.uuid, user,
                reclaim_ip
            )
        elif action_name == 'Terminate':
            destroy_instance(user, identity.uuid, instance.id)
        else:
            raise Exception("Encountered Unknown Action Named %s" % action_name)
    except ObjectDoesNotExist:
        # This may be unreachable when null,blank = True
        logger.debug(
            "Provider %s - 'Do Nothing' for Over Allocation" % identity.provider
        )
        return


def _cleanup_missing_instances(
    identity, core_running_instances, start_date=None
):
    """
    Cleans up the DB InstanceStatusHistory when you know what instances are
    active...

    core_running_instances - Reference list of KNOWN active instances
    """
    instances = []

    if not identity:
        return instances

    core_instances = _core_instances_for(identity, start_date)
    fixed_instances = []
    for inst in core_instances:
        if not core_running_instances or inst not in core_running_instances:
            inst.end_date_all()
            fixed_instances.append(inst)
        else:
            # Instance IS in the list of running instances.. Further cleaning
            # can be done at this level.
            non_end_dated_history = inst.instancestatushistory_set.filter(
                end_date=None
            )
            count = len(non_end_dated_history)
            if count > 1:
                history_names = [
                    ish.status.name for ish in non_end_dated_history
                ]
                # Note: We have the 'wrong' instance, we want the one that
                # includes the ESH driver
                core_running_inst = [
                    i for i in core_running_instances if i == inst
                ][0]
                new_history = _resolve_history_conflict(
                    identity, core_running_inst, non_end_dated_history
                )
                fixed_instances.append(inst)
                logger.warn(
                    "Instance %s contained %s "
                    "NON END DATED history:%s. "
                    " New History: %s" %
                    (inst.provider_alias, count, history_names, new_history)
                )
            # Gather the updated values..
            instances.append(inst)
    # Return the updated list
    if fixed_instances:
        logger.warn(
            "Cleaned up %s instances for %s" %
            (len(fixed_instances), identity.created_by.username)
        )
    return instances


def _resolve_history_conflict(
    identity, core_running_instance, bad_history, reset_time=None
):
    """
    NOTE 1: This is a 'band-aid' fix until we are 100% that Transaction will
            not create conflicting un-end-dated objects.

    NOTE 2: It is EXPECTED that this instance has the 'esh' attribute
            Failure to add the 'esh' attribute will generate a ValueError!
    """
    if not getattr(core_running_instance, 'esh'):
        raise ValueError("Esh is missing from %s" % core_running_instance)
    esh_instance = core_running_instance.esh

    # Check for temporary status and fetch that
    tmp_status = esh_instance.extra.get('metadata', {}).get("tmp_status")
    new_status = tmp_status or esh_instance.extra['status']

    esh_driver = get_cached_driver(identity=identity)
    new_size = _esh_instance_size_to_core(
        esh_driver, esh_instance, identity.provider.uuid
    )
    if not reset_time:
        reset_time = timezone.now()
    for history in bad_history:
        history.end_date = reset_time
        history.save()
    new_history = InstanceStatusHistory.create_history(
        new_status, core_running_instance, new_size, reset_time
    )
    return new_history


def _get_instance_owner_map(provider, users=None):
    """
    All keys == All identities
    Values = List of identities / username
    NOTE: This is KEYSTONE && NOVA specific. the 'instance owner' here is the
          username // ex_tenant_name
    """
    from service.driver import get_account_driver

    accounts = get_account_driver(provider=provider, raise_exception=True)
    all_identities = _select_identities(provider, users)
    acct_providers = AccountProvider.objects.filter(provider=provider)
    if acct_providers:
        account_identity = acct_providers[0].identity
        provider = None
    else:
        account_identity = None

    all_instances = get_cached_instances(
        provider=provider, identity=account_identity, force=True
    )
    #all_tenants = admin_driver._connection._keystone_list_tenants()
    all_tenants = accounts.list_projects()
    # Convert instance.owner from tenant-id to tenant-name all at once
    all_instances = _convert_tenant_id_to_names(all_instances, all_tenants)
    # Make a mapping of owner-to-instance
    instance_map = _make_instance_owner_map(all_instances, users=users)
    logger.info("Instance owner map created")
    identity_map = _include_all_idents(all_identities, instance_map)
    logger.info("Identity map created")
    return identity_map


# Used in OLD allocation


def filter_allocation_source_instances(allocation_source, user, esh_instances):
    as_instances = []
    for inst in esh_instances:
        core_instance = CoreInstance.objects.filter(
            created_by=user, provider_alias=inst.id
        ).first()
        if not core_instance:
            logger.debug(
                "Skipping Instance %s -- not included in DB." % inst.id
            )
            continue
        assert isinstance(core_instance, CoreInstance)
        instance_allocation_source = core_instance.allocation_source
        if not instance_allocation_source:
            logger.debug(
                "Skipping Instance %s -- no allocation source set." % inst.id
            )
            continue
        if instance_allocation_source != allocation_source:
            logger.debug(
                "Skipping Instance %s -- Allocation source mismatch." % inst.id
            )
            continue
        as_instances.append(inst)
    return as_instances


def allocation_source_overage_enforcement_for(
    allocation_source, user, identity
):
    logger.debug(
        "allocation_source_overage_enforcement_for - allocation_source: %s, user: %s, identity: %s",
        allocation_source, user, identity
    )
    provider = identity.provider
    action = provider.over_allocation_action
    logger.debug(
        "allocation_source_overage_enforcement_for - provider.over_allocation_action: %s",
        provider.over_allocation_action
    )
    if not action:
        logger.debug("No 'over_allocation_action' provided for %s", provider)
        return []    # Over_allocation was not attempted
    if not settings.ENFORCING:
        logger.info("Settings dictate that ENFORCING = False. Returning..")
        return []
    try:
        driver = get_cached_driver(identity=identity)
        esh_instances = driver.list_instances()
    except LibcloudInvalidCredsError:
        raise Exception(
            "User %s has invalid credentials on Identity %s" % (user, identity)
        )
    filtered_instances = filter_allocation_source_instances(
        allocation_source, user, esh_instances
    )
    # TODO: Parallelize this operation so you don't wait for larger instances
    # to finish 'wait_for' task below..
    instances = []
    for instance in filtered_instances:
        core_instance = execute_provider_action(
            user, driver, identity, instance, action
        )
        instances.append(core_instance)
    return instances


def execute_provider_action(user, driver, identity, instance, action):
    logger.debug(
        'execute_provider_action - user: %s, driver: %s, identity: %s, instance: %s, action: %s',
        user, driver, identity, instance, action
    )
    try:
        if driver._is_active_instance(instance):
            # Suspend active instances, update the task in the DB
            # NOTE: identity.created_by COULD BE the Admin User, indicating that this action/InstanceHistory was
            #       executed by the administrator.. Future Release Idea.
            _execute_provider_action(
                identity, identity.created_by, instance, action.name
            )
            # NOTE: Intentionally added to allow time for
            #      the Cloud to begin 'suspend' operation
            #      before querying for the instance again.
            # TODO: Instead: Add "wait_for" change from active to any
            # terminal, non-active state?
            wait_time = random.uniform(2, 6)
            time.sleep(wait_time)
            updated_esh = driver.get_instance(instance.id)
            core_instance = convert_esh_instance(
                driver, updated_esh, identity.provider.uuid, identity.uuid, user
            )
            return core_instance
        else:
            logger.debug(
                '_is_active_instance is False, so not calling _execute_provider_action for instance %s',
                instance
            )
    except Exception as e:
        # Raise ANY exception that doesn't say
        # 'This instance is already in the requested VM state'
        # NOTE: This is OpenStack specific
        logger.debug('execute_provider_action - exception: %s', e)
        if 'in vm_state' not in e.message:
            logger.exception('execute_provider_action failed')
            raise
