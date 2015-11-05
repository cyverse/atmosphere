from datetime import timedelta

from django.utils import timezone
from django.db.models import Q

from celery.decorators import task

from core.query import only_current, only_current_machines, only_current_apps, only_current_source, source_in_range
from core.models.size import Size, convert_esh_size
from core.models.instance import convert_esh_instance
from core.models.provider import Provider
from core.models.machine import get_or_create_provider_machine, ProviderMachine
from core.models.application import Application, ApplicationMembership
from core.models import Allocation, Credential

from service.monitoring import\
    _cleanup_missing_instances,\
    _get_instance_owner_map, \
    _get_identity_from_tenant_name
from service.monitoring import user_over_allocation_enforcement
from service.driver import get_account_driver
from service.cache import get_cached_driver
from glanceclient.exc import HTTPNotFound

from threepio import celery_logger


def strfdelta(tdelta, fmt=None):
    from string import Formatter
    if not fmt:
        # The standard, most human readable format.
        fmt = "{D} days {H:02} hours {M:02} minutes {S:02} seconds"
    if tdelta == timedelta():
        return "0 minutes"
    formatter = Formatter()
    return_map = {}
    div_by_map = {'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
    keys = map(lambda x: x[1], list(formatter.parse(fmt)))
    remainder = int(tdelta.total_seconds())

    for unit in ('D', 'H', 'M', 'S'):
        if unit in keys and unit in div_by_map.keys():
            return_map[unit], remainder = divmod(remainder, div_by_map[unit])

    return formatter.format(fmt, **return_map)


def strfdate(datetime_o, fmt=None):
    if not fmt:
        # The standard, most human readable format.
        fmt = "%m/%d/%Y %H:%M:%S"
    if not datetime_o:
        datetime_o = timezone.now()

    return datetime_o.strftime(fmt)


def tenant_id_to_name_map(account_driver):
    """
    INPUT: account driver
    Get a list of projects
    OUTPUT: A dictionary with keys of ID and values of name
    """
    all_projects = account_driver.list_projects()
    return {tenant.id : tenant.name for tenant in all_projects}


@task(name="monitor_machines")
def monitor_machines():
    """
    Update machines by querying the Cloud for each active provider.
    """
    for p in Provider.get_active():
        monitor_machines_for.apply_async(args=[p.id])


@task(name="prune_machines_for")
def prune_machines_for(provider_id, print_logs=False, dry_run=False, forced_removal=False):
    """
    Look at the list of machines (as seen by the AccountProvider)
    if a machine cannot be found in the list, remove it.
    NOTE: BEFORE CALLING THIS TASK you should ensure that the AccountProvider can see ALL images. Failure to do so will result in any unseen image to be prematurely end-dated and removed from the API/UI.
    """
    provider = Provider.objects.get(id=provider_id)

    if print_logs:
        import logging
        import sys
        consolehandler = logging.StreamHandler(sys.stdout)
        consolehandler.setLevel(logging.DEBUG)
        celery_logger.addHandler(consolehandler)

    if provider.is_active():
        account_driver = get_account_driver(provider)
        db_machines = ProviderMachine.objects.filter(only_current_source(), instance_source__provider=provider)
        all_projects_map = tenant_id_to_name_map(account_driver)
        cloud_machines = account_driver.list_all_images()
    else:
        db_machines = ProviderMachine.objects.filter(
                source_in_range(),
                instance_source__provider=provider)
        cloud_machines = []
    # Don't do anything if cloud machines == [None,[]]
    if not cloud_machines and not forced_removal:
        return

    # Loop1 - End-date All machines in the DB that can NOT be found in the cloud.
    cloud_machine_ids = [mach.id for mach in cloud_machines]
    for machine in db_machines:
        cloud_match = [mach for mach in cloud_machine_ids if mach == machine.identifier]
        if not cloud_match:
            remove_machine(machine, dry_run=dry_run)

    if print_logs:
        celery_logger.removeHandler(consolehandler)

@task(name="monitor_machines_for")
def monitor_machines_for(provider_id, print_logs=False, dry_run=False):
    """
    Run the set of tasks related to monitoring machines for a provider.
    Optionally, provide a list of usernames to monitor
    While debugging, print_logs=True can be very helpful.
    start_date and end_date allow you to search a 'non-standard' window of time.

    NEW LOGIC:
    * Membership and Privacy is dictated at the APPLICATION level.
    * loop over all machines on the cloud
    *   * If machine is PUBLIC, ensure the APP is public.
    *   * If machine is PRIVATE, ensure the APP is private && sync the membership!
    *   * Ignore the possibility of conflicts, prior schema should be sufficient for ensuring the above two usecases
    """
    provider = Provider.objects.get(id=provider_id)

    if print_logs:
        import logging
        import sys
        consolehandler = logging.StreamHandler(sys.stdout)
        consolehandler.setLevel(logging.DEBUG)
        celery_logger.addHandler(consolehandler)

    #STEP 1: get the apps
    new_public_apps, private_apps = get_public_and_private_apps(provider)

    #STEP 2: Find conflicts and report them.
    intersection = set(private_apps.keys()) & set(new_public_apps)
    if intersection:
        raise Exception("These applications were listed as BOTH public && private apps. Manual conflict correction required: %s" % intersection)

    #STEP 3: Apply the changes at app-level
    #Memoization at this high of a level will help save time
    account_drivers = {} # Provider -> accountDriver
    provider_tenant_mapping = {}  # Provider -> [{TenantId : TenantName},...]
    image_maps = {}
    for app in new_public_apps:
        make_machines_public(app, account_drivers, dry_run=dry_run)

    for app, membership in private_apps.items():
        make_machines_private(app, membership, account_drivers, provider_tenant_mapping, image_maps, dry_run=dry_run)

    if print_logs:
        celery_logger.removeHandler(consolehandler)
    return

def get_public_and_private_apps(provider):
    """
    INPUT: Provider provider
    OUTPUT: 2-tuple (
            new_public_apps [],
            private_apps(key) + super-set-membership(value) {})
    """
    account_driver = get_account_driver(provider)
    all_projects_map = tenant_id_to_name_map(account_driver)
    cloud_machines = account_driver.list_all_images()

    db_machines = ProviderMachine.objects.filter(only_current_source(), instance_source__provider=provider)
    new_public_apps = []
    private_apps = {}
    # ASSERT: All non-end-dated machines in the DB can be found in the cloud
    # if you do not believe this is the case, you should call 'prune_machines_for'
    for cloud_machine in cloud_machines:
        #Filter out: ChromoSnapShot, eri-, eki-, ... (Or dont..)
        if any(cloud_machine.name.startswith(prefix) for prefix in ['eri-','eki-', 'ChromoSnapShot']):
            #celery_logger.debug("Skipping cloud machine %s" % cloud_machine)
            continue
        db_machine = get_or_create_provider_machine(cloud_machine.id, cloud_machine.name, provider.uuid)
        db_version = db_machine.application_version
        db_application = db_version.application

        if cloud_machine.is_public:
            if db_application.private and db_application not in new_public_apps:
                new_public_apps.append(db_application) #Distinct list..
            #Else the db app is public and no changes are necessary.
        else:
            # cloud machine is private
            membership = get_shared_identities(account_driver, cloud_machine, all_projects_map)
            all_members = private_apps.get(db_application, [])
            all_members.extend(membership)
            #Distinct list..
            private_apps[db_application] = all_members
    return new_public_apps, private_apps


def remove_machine(db_machine, now_time=None, dry_run=False):
    """
    End date the DB ProviderMachine
    If all PMs are end-dated, End date the ApplicationVersion
    if all Versions are end-dated, End date the Application
    """
    if not now_time:
        now_time = timezone.now()

    db_machine.end_date = now_time
    celery_logger.info("End dating machine: %s" % db_machine)
    if not dry_run:
        db_machine.save()

    db_version = db_machine.application_version
    if db_version.machines.filter(
            # Look and see if all machines are end-dated.
            Q(instance_source__end_date__isnull=True) |
            Q(instance_source__end_date__gt=now_time)
            ).count() != 0:
        # Other machines exist.. No cascade necessary.
        return True
    # Version also completely end-dated. End date this version.
    db_version.end_date = now_time
    celery_logger.info("End dating version: %s" % db_version)
    if not dry_run:
        db_version.save()

    db_application = db_version.application
    if db_application.versions.filter(
            # If all versions are end-dated
            only_current(now_time)
            ).count() != 0:
        # Other versions exist.. No cascade necessary..
        return True
    db_application.end_date = now_time
    celery_logger.info("End dating application: %s" % db_application)
    if not dry_run:
        db_application.save()
    return True


def make_machines_private(application, identities, account_drivers={}, provider_tenant_mapping={}, image_maps={}, dry_run=False):
    """
    This method is called when the DB has marked the Machine/Application as PUBLIC
    But the CLOUD states that the machine is really private.
    GOAL: All versions and machines will be listed as PRIVATE on the cloud and include AS MANY identities as exist.
    """
    for version in application.active_versions():
        for machine in version.active_machines():
            # For each *active* machine in app/version..
            # Loop over each identity and check the list of 'current tenants' as viewed by keystone.
            account_driver = memoized_driver(machine, account_drivers)
            tenant_name_mapping = memoized_tenant_name_map(account_driver, provider_tenant_mapping)
            current_tenants = get_current_members(
                    account_driver, machine, tenant_name_mapping)
            provider = machine.instance_source.provider
            cloud_machine = memoized_image(account_driver, machine, image_maps)
            for identity in identities:
                if identity.provider == provider:
                    _share_image(account_driver, cloud_machine, identity, current_tenants, dry_run=dry_run)
                    add_application_membership(application, identity, dry_run=dry_run)
    # All the cloud work has been completed, so "lock down" the application.
    if application.private == False:
        application.private = True
        celery_logger.info("Making Application %s private" % application.name)
        if not dry_run:
            application.save()

def memoized_image(account_driver, db_machine, image_maps={}):
    provider = db_machine.instance_source.provider
    identifier = db_machine.instance_source.identifier
    cloud_machine = image_maps.get( (provider, identifier) )
    # Return memoized result
    if cloud_machine:
        return cloud_machine
    # Retrieve and remember
    cloud_machine = account_driver.get_image(identifier)
    image_maps[ (provider, identifier) ] = cloud_machine
    return cloud_machine

def memoized_driver(machine, account_drivers={}):
    provider = machine.instance_source.provider
    account_driver = account_drivers.get(provider)
    if not account_driver:
        account_driver = get_account_driver(provider)
        if not account_driver:
            raise Exception("Cannot instantiate an account driver for %s" % provider)
        account_drivers[provider] = account_driver
    return account_driver

def memoized_tenant_name_map(account_driver, tenant_list_maps={}):
    tenant_id_name_map = tenant_list_maps.get(account_driver.core_provider)
    if not tenant_id_name_map:
        tenant_id_name_map = tenant_id_to_name_map(account_driver)
        tenant_list_maps[account_driver.core_provider] = tenant_id_name_map

    return tenant_id_name_map

def get_current_members(account_driver, machine, tenant_id_name_map):
    current_membership = account_driver.image_manager.shared_images_for(
            image_id=machine.identifier)

    current_tenants = []
    for membership in current_membership:
        tenant_id = membership.member_id
        tenant_name = tenant_id_name_map.get(tenant_id)
        if tenant_name:
            current_tenants.append(tenant_name)
    return current_tenants

def _share_image(account_driver, cloud_machine, identity, members, dry_run=False):
    """
    INPUT: use account_driver to share cloud_machine with identity (if not in 'members' list)
    """
    # Skip tenant-names who are NOT in the DB, and tenants who are already included
    missing_tenant = identity.credential_set.filter(~Q(value__in=members), key='ex_tenant_name')
    if missing_tenant.count() == 0:
        #celery_logger.debug("SKIPPED _ Image %s already shared with %s" % (cloud_machine.id, identity))
        return
    elif missing_tenant.count() > 1:
        raise Exception("Safety Check -- You should not be here")
    tenant_name = missing_tenant[0]
    if cloud_machine.is_public == True:
        celery_logger.info("Making Machine %s private" % cloud_machine.id)
        cloud_machine.update(is_public=False)

    celery_logger.info("Sharing image %s<%s>: %s with %s" % (cloud_machine.id, cloud_machine.name, identity.provider.location, tenant_name.value))
    if not dry_run:
        account_driver.image_manager.share_image(cloud_machine, tenant_name.value)

def add_application_membership(application, identity, dry_run=False):
    for membership_obj in identity.identitymembership_set.all():
        # For every 'member' of this identity:
        group = membership_obj.member
        # Add an application membership if not already there
        if application.applicationmembership_set.filter(group=group).count() == 0:
            celery_logger.info("Added ApplicationMembership %s for %s" % (group.name, application.name))
            if not dry_run:
                ApplicationMembership.objects.create(application=application, group=group)
        else:
            #celery_logger.debug("SKIPPED _ Group %s already ApplicationMember for %s" % (group.name, application.name))
            pass

def get_shared_identities(account_driver, cloud_machine, tenant_id_name_map):
    """
    INPUT: Provider, Cloud Machine (private), mapping of tenant_id to tenant_name
    OUTPUT: List of identities that *include* the 'tenant name' credential matched to 'a shared user' in openstack.
    """
    from core.models import Identity
    cloud_membership = account_driver.image_manager.shared_images_for(
        image_id=cloud_machine.id)
    # NOTE: the START type of 'all_identities' is list (in case no ValueListQuerySet is ever found)
    all_identities = []
    for cloud_machine_membership in cloud_membership:
        tenant_id = cloud_machine_membership.member_id
        tenant_name = tenant_id_name_map.get(tenant_id)
        if not tenant_name:
            celery_logger.warn("TENANT ID: %s NOT FOUND - %s" % (tenant_id, cloud_machine_membership))
            continue
        # Find matching 'tenantName' credential and add all matching identities w/ that tenantName.
        matching_creds = Credential.objects.filter(
                key='ex_tenant_name',  # TODO: ex_project_name on next OStack update.
                value=tenant_name,
                # NOTE: re-add this line when not replicating clouds!
                #identity__provider=account_driver.core_provider)
                )
        identity_ids = matching_creds.values_list('identity', flat=True)
        if not all_identities:
            all_identities = identity_ids
        else:
            all_identities = all_identities | identity_ids
    identity_list = Identity.objects.filter(id__in=all_identities)
    return identity_list

def update_membership(application, shared_identities):
    """
    For machine in application/version:
        Get list of current users
        For "super-set" list of identities:
            if identity exists on provider && identity NOT in current user list:
                account_driver.add_user(identity.name)
    """
    db_identity_membership = identity.identitymembership_set.all().distinct()
    for db_identity_member in db_identity_membership:
        # For each group who holds this identity:
        #   grant them access to the now-private App, Version & Machine
        db_group = db_identity_member.member
        ApplicationMembership.objects.get_or_create(
            application=application, group=db_group)
        celery_logger.info("Added Application, Version, and Machine Membership to Group: %s" % (db_group,))
    return application


def make_machines_public(application, account_drivers={}, dry_run=False):
    """
    This method is called when the DB has marked the Machine/Application as PRIVATE
    But the CLOUD states that the machine is really public.
    """
    for version in application.active_versions():
        for machine in version.active_machines():
            provider = machine.instance_source.provider
            account_driver = memoized_driver(machine, account_drivers)
            image = account_driver.image_manager.get_image(image_id=machine.identifier)
            if image and image.is_public == False:
                celery_logger.info("Making Machine %s public" % image.id)
                if not dry_run:
                    image.update(is_public=True)
    # Set top-level application to public (This will make all versions and PMs public too!)
    application.private = False
    celery_logger.info("Making Application %s public" % application.name)
    if not dry_run:
        application.save()


@task(name="monitor_instances")
def monitor_instances():
    """
    Update instances for each active provider.
    """
    for p in Provider.get_active():
        monitor_instances_for.apply_async(args=[p.id])


@task(name="monitor_instances")
def monitor_instance_allocations():
    """
    Update instances for each active provider.
    """
    for p in Provider.get_active():
        monitor_instances_for.apply_async(args=[p.id], check_allocations=True)


@task(name="monitor_instances_for")
def monitor_instances_for(provider_id, users=None,
                          print_logs=False, check_allocations=False, start_date=None, end_date=None):
    """
    Run the set of tasks related to monitoring instances for a provider.
    Optionally, provide a list of usernames to monitor
    While debugging, print_logs=True can be very helpful.
    start_date and end_date allow you to search a 'non-standard' window of time.
    """
    provider = Provider.objects.get(id=provider_id)

    # For now, lets just ignore everything that isn't openstack.
    if 'openstack' not in provider.type.name.lower():
        return

    instance_map = _get_instance_owner_map(provider, users=users)

    if print_logs:
        import logging
        import sys
        consolehandler = logging.StreamHandler(sys.stdout)
        consolehandler.setLevel(logging.DEBUG)
        celery_logger.addHandler(consolehandler)

    # DEVNOTE: Potential slowdown running multiple functions
    # Break this out when instance-caching is enabled
    running_total = 0
    for username in sorted(instance_map.keys()):
        running_instances = instance_map[username]
        running_total += len(running_instances)
        identity = _get_identity_from_tenant_name(provider, username)
        if identity and running_instances:
            try:
                driver = get_cached_driver(identity=identity)
                core_running_instances = [
                    convert_esh_instance(
                        driver,
                        inst,
                        identity.provider.uuid,
                        identity.uuid,
                        identity.created_by) for inst in running_instances]
            except Exception as exc:
                celery_logger.exception(
                    "Could not convert running instances for %s" %
                    username)
                continue
        else:
            # No running instances.
            core_running_instances = []
        # Using the 'known' list of running instances, cleanup the DB
        core_instances = _cleanup_missing_instances(
            identity,
            core_running_instances)
        if check_allocations:
            allocation_result = user_over_allocation_enforcement(
                provider, username,
                print_logs, start_date, end_date)
    if print_logs:
        celery_logger.removeHandler(consolehandler)
    return running_total


@task(name="monitor_sizes")
def monitor_sizes():
    """
    Update sizes for each active provider.
    """
    for p in Provider.get_active():
        monitor_sizes_for.apply_async(args=[p.id])


@task(name="monitor_sizes_for")
def monitor_sizes_for(provider_id, print_logs=False):
    """
    Run the set of tasks related to monitoring sizes for a provider.
    Optionally, provide a list of usernames to monitor
    While debugging, print_logs=True can be very helpful.
    start_date and end_date allow you to search a 'non-standard' window of time.
    """
    from service.driver import get_admin_driver

    if print_logs:
        import logging
        import sys
        consolehandler = logging.StreamHandler(sys.stdout)
        consolehandler.setLevel(logging.DEBUG)
        celery_logger.addHandler(consolehandler)

    provider = Provider.objects.get(id=provider_id)
    admin_driver = get_admin_driver(provider)
    # Non-End dated sizes on this provider
    db_sizes = Size.objects.filter(only_current(), provider=provider)
    all_sizes = admin_driver.list_sizes()
    seen_sizes = []
    for cloud_size in all_sizes:
        core_size = convert_esh_size(cloud_size, provider.uuid)
        seen_sizes.append(core_size)

    now_time = timezone.now()
    needs_end_date = [size for size in db_sizes if size not in seen_sizes]
    for size in needs_end_date:
        celery_logger.debug("End dating inactive size: %s" % size)
        size.end_date = now_time
        size.save()

    if print_logs:
        celery_logger.removeHandler(consolehandler)


@task(name="monthly_allocation_reset")
def monthly_allocation_reset():
    """
    This task contains logic related to:
    * Providers whose allocations should be reset on the first of the month
    * Which Allocation will be used as 'default'
    """
    default_allocation = Allocation.default_allocation()
    provider = Provider.objects.get(location='iPlant Cloud - Tucson')
    reset_provider_allocation.apply_async(
        args=[
            provider.id,
            default_allocation.id])


@task(name="reset_provider_allocation")
def reset_provider_allocation(provider_id, default_allocation_id):
    provider = Provider.objects.get(id=provider_id)
    default_allocation = Allocation.objects.get(id=default_allocation_id)
    exempt_allocation_list = Allocation.objects.filter(threshold=-1)
    users_reset = 0
    memberships_reset = []
    for ident in provider.identity_set.all():
        if ident.created_by.is_staff or ident.created_by.is_superuser:
            continue
        for membership in ident.identitymembership_set.all():
            if membership.allocation_id == default_allocation.id:
                continue
            if membership.allocation_id in exempt_allocation_list:
                continue
            print "Resetting Allocation for %s \t\tOld Allocation:%s" % (membership.member.name, membership.allocation)
            membership.allocation = default_allocation
            membership.save()
            memberships_reset.append(membership)
            users_reset += 1
    return (users_reset, memberships_reset)
