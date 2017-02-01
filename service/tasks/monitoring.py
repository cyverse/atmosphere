from datetime import timedelta

from django.conf import settings
from django.db.models import Q, Count
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from celery.decorators import task

from core.query import (
    only_current, only_current_source,
    source_in_range, inactive_versions)
from core.models.group import Group
from core.models.size import Size, convert_esh_size
from core.models.volume import Volume, convert_esh_volume
from core.models.instance import convert_esh_instance
from core.models.provider import Provider
from core.models.machine import convert_glance_image, get_or_create_provider_machine, ProviderMachine, ProviderMachineMembership
from core.models.application import Application, ApplicationMembership
from core.models.allocation_source import AllocationSource
from core.models.event_table import EventTable
from core.models.application_version import ApplicationVersion
from core.models import Allocation, Credential, IdentityMembership

from service.machine import (
    update_db_membership_for_group,
    update_cloud_membership_for_machine
)
from service.monitoring import (
    _cleanup_missing_instances,
    _get_instance_owner_map,
    _get_identity_from_tenant_name,
    allocation_source_overage_enforcement
)
from service.monitoring import user_over_allocation_enforcement
from service.driver import get_account_driver
from service.cache import get_cached_driver
from rtwo.exceptions import GlanceConflict, GlanceForbidden

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
    return {tenant.id: tenant.name for tenant in all_projects}


@task(name="prune_machines")
def prune_machines():
    """
    Query the cloud and remove any machines
    that exist in the DB but can no longer be found.
    """
    for p in Provider.get_active():
        prune_machines_for.apply_async(args=[p.id])


@task(name="prune_machines_for")
def prune_machines_for(
        provider_id, print_logs=False, dry_run=False, forced_removal=False):
    """
    Look at the list of machines (as seen by the AccountProvider)
    if a machine cannot be found in the list, remove it.
    NOTE: BEFORE CALLING THIS TASK you should ensure
    that the AccountProvider can see ALL images.
    Failure to do so will result in any image unseen by the admin
    to be prematurely end-dated and removed from the API/UI.
    """
    provider = Provider.objects.get(id=provider_id)
    now = timezone.now()
    if print_logs:
        console_handler = _init_stdout_logging()
    celery_logger.info("Starting prune_machines for Provider %s @ %s"
                       % (provider, now))

    if provider.is_active():
        account_driver = get_account_driver(provider)
        db_machines = ProviderMachine.objects.filter(
            only_current_source(), instance_source__provider=provider)
        cloud_machines = account_driver.list_all_images()
    else:
        db_machines = ProviderMachine.objects.filter(
                source_in_range(),  # like 'only_current..' w/o active_provider
                instance_source__provider=provider)
        cloud_machines = []

    # Don't do anything if cloud machines == [None,[]]
    if not cloud_machines and not forced_removal:
        return

    # Loop 1 - End-date All machines in the DB that
    # can NOT be found in the cloud.
    mach_count = _end_date_missing_database_machines(
        db_machines, cloud_machines, now=now, dry_run=dry_run)

    # Loop 2 and 3 - Capture all (still-active) versions without machines,
    # and all applications without versions.
    # These are 'outliers' and mainly here for safety-check purposes.
    ver_count = _remove_versions_without_machines(now=now)
    app_count = _remove_applications_without_versions(now=now)

    # Loop 4 - All 'Application' DB objects require
    # >=1 Version with >=1 ProviderMachine (ACTIVE!)
    # Apps that don't meet this criteria should be end-dated.
    app_count += _update_improperly_enddated_applications(now)

    celery_logger.info(
        "prune_machines completed for Provider %s : "
        "%s Applications, %s versions and %s machines pruned."
        % (provider, app_count, ver_count, mach_count))
    if print_logs:
        _exit_stdout_logging(console_handler)


@task(name="monitor_machines")
def monitor_machines():
    """
    Update machines by querying the Cloud for each active provider.
    """
    for p in Provider.get_active():
        monitor_machines_for.apply_async(args=[p.id])


@task(name="monitor_machines_for")
def monitor_machines_for(provider_id, print_logs=False, dry_run=False):
    """
    Run the set of tasks related to monitoring machines for a provider.
    Optionally, provide a list of usernames to monitor
    While debugging, print_logs=True can be very helpful.
    start_date and end_date allow you to search a 'non-standard' window of time.

    NEW LOGIC:
    """
    provider = Provider.objects.get(id=provider_id)

    if print_logs:
        console_handler = _init_stdout_logging()

    account_driver = get_account_driver(provider)
    cloud_machines = account_driver.list_all_images()

    # ASSERT: All non-end-dated machines in the DB can be found in the cloud
    # if you do not believe this is the case, you should call 'prune_machines_for'
    for cloud_machine in cloud_machines:
        if not machine_is_valid(cloud_machine, account_driver):
            continue
        owner_project = _get_owner(account_driver, cloud_machine)
        #STEP 1: Get the application, version, and provider_machine registered in Atmosphere
        (db_machine, created) = convert_glance_image(cloud_machine, provider.uuid, owner_project)
        #STEP 2: For any private cloud_machine, convert the 'shared users' as known by cloud
        update_image_membership(account_driver, cloud_machine, db_machine)

        # into DB relationships: ApplicationVersionMembership, ProviderMachineMembership
        #STEP 3: if ENFORCING -- occasionally 're-distribute' any ACLs that are *listed on DB but not on cloud* -- removals should be done explicitly, outside of this function
        if settings.ENFORCING:
            distribute_image_membership(account_driver, cloud_machine, provider)
        # ASSERTIONS about this method: 
        # 1) We will never 'remove' membership,
        # 2) We will never 'remove' a public or private flag as listed in application.
        # 2b) Future: Individual versions/machines as described by relationships above dictate whats shown in the application.

    if print_logs:
        _exit_stdout_logging(console_handler)
    return

def _get_owner(accounts, cloud_machine):
    """
    For a given cloud machine, attempt to find the owners username
    Priority is given to 'owner' which will point to the projectId/tenantId that created the image
    Otherwise, accept the 'application_owner' (Older openstack+glance may not have 'owner' attribute)
    """
    owner = cloud_machine.get('owner')
    if owner:
        owner_project = accounts.get_project_by_id(owner)
    else:
        owner = cloud_machine.get('application_owner')
        owner_project = accounts.get_project(owner)
    return owner_project

def machine_is_valid(cloud_machine, accounts):
    """
    As the criteria for "what makes a glance image an atmosphere ProviderMachine" changes, we can use this function to hook out to external plugins, etc.
    Filters out:
        - ChromoSnapShot, eri-, eki-
        - Private images not shared with atmosphere accounts
        - Domain-specific image catalog(?)
    """
    provider = accounts.core_provider
    # If the name of the machine indicates that it is a Ramdisk, Kernel, or Chromogenic Snapshot, skip it.
    if any(cloud_machine.name.startswith(prefix) for prefix in ['eri-','eki-', 'ChromoSnapShot']):
        celery_logger.info("Skipping cloud machine %s" % cloud_machine)
        return False
    # If the metadata 'skip_atmosphere' is found, do not add the machine.
    if cloud_machine.get('skip_atmosphere', False):
        celery_logger.info("Skipping cloud machine %s - Includes 'skip_atmosphere' metadata" % cloud_machine)
        return False
    # If the metadata indicates that the image-type is snapshot -- skip it.
    if cloud_machine.get('image_type', 'image') == 'snapshot':
        celery_logger.info("Skipping cloud machine %s - Image type indicates a snapshot" % cloud_machine)
        return False
    owner_project = _get_owner(accounts, cloud_machine)
    # If the image is private, ensure that an owner can be found inside the system.
    if cloud_machine.get('visibility', '') == 'private':
        shared_with_projects = accounts.shared_images_for(cloud_machine.id)
        shared_with_projects.append(owner_project)
        project_names = [p.name for p in shared_with_projects if p]  # TODO: better error handling here
        identity_matches = provider.identity_set.filter(
            credential__key='ex_project_name', credential__value__in=project_names).count() > 0
        if not identity_matches:
            celery_logger.info("Skipping private machine %s - The owner does not exist in Atmosphere" % cloud_machine)
            return False
    if accounts.provider_creds.get('ex_force_auth_version', '2.0_password') != '3.x_password':
        return True
    # NOTE: Potentially if we wanted to do 'domain-restrictions' *inside* of atmosphere,
    # we could do that (based on the domain of the image owner) here.
    domain_id = owner_project.domain_id
    config_domain = accounts.get_config('user', 'domain', 'default')
    owner_domain = accounts.openstack_sdk.identity.get_domain(domain_id)
    account_domain = accounts.openstack_sdk.identity.get_domain(config_domain)
    if owner_domain.id != account_domain.id: # and if FLAG FOR DOMAIN-SPECIFIC ATMOSPHERE
        celery_logger.info("Skipping private machine %s - The owner belongs to a different domain (%s)" % (cloud_machine, owner_domain))
        return False
    return True


def distribute_image_membership(account_driver, cloud_machine, provider):
    """
    Based on what we know about the DB, at a minimum, ensure that their projects are added to the image_members list for this cloud_machine.
    """
    pm = ProviderMachine.objects.get(
        instance_source__provider=provider,
        instance_source__identifier=cloud_machine.id)
    group_ids = ProviderMachineMembership.objects.filter(provider_machine=pm).values_list('group', flat=True)
    groups = Group.objects.filter(id__in=group_ids)
    for group in groups:
        update_cloud_membership_for_machine(pm, group)


def update_image_membership(account_driver, cloud_machine, db_machine):
    """
    Given a cloud_machine and db_machine, create any relationships possible for ProviderMachineMembership and ApplicationVersionMembership
    """
    image_visibility = cloud_machine.get('visibility','private')
    if image_visibility.lower() == 'public':
        return
    image_owner = cloud_machine.get('application_owner','')
    #TODO: In a future update to 'imaging' we might image 'as the user' rather than 'as the admin user', in this case we should just use 'owner' metadata
    shared_group_names = [image_owner]
    shared_projects = account_driver.shared_images_for(cloud_machine.id)
    shared_group_names.extend(p.name for p in shared_projects if p)
    groups = Group.objects.filter(name__in=shared_group_names)
    if not groups:
        return
    for group in groups:
        update_db_membership_for_group(db_machine, group)



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

        if cloud_machine.get('visibility') == 'public':
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
    if not application.private:
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

def add_application_membership(application, identity, dry_run=False):
    for membership_obj in identity.identity_memberships.all():
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
    db_identity_membership = identity.identity_memberships.all().distinct()
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
            try:
                image = account_driver.image_manager.get_image(image_id=machine.identifier)
            except:  # Image not found
                celery_logger.info("Image not found on this provider: %s" % (machine))
                continue

            image_is_public = image.is_public if hasattr(image,'is_public') else image.get('visibility','') == 'public'
            if image and image_is_public == False:
                celery_logger.info("Making Machine %s public" % image.id)
                if not dry_run:
                    account_driver.image_manager.glance.images.update(image.id, visibility='public')
    # Set top-level application to public (This will make all versions and PMs public too!)
    application.private = False
    celery_logger.info("Making Application %s:%s public" % (application.id,application.name))
    if not dry_run:
        application.save()


@task(name="monitor_instances")
def monitor_instances():
    """
    Update instances for each active provider.
    """
    for p in Provider.get_active():
        monitor_instances_for.apply_async(args=[p.id])


@task(name="enforce_allocation_overage")
def enforce_allocation_overage(allocation_source_id):
    """
    Update instances for each active provider.
    """
    allocation_source = AllocationSource.objects.get(source_id=allocation_source_id)
    user_instances_enforced = allocation_source_overage_enforcement(allocation_source)
    EventTable.create_event(
        name="allocation_source_threshold_enforced",
        entity_id=source.source_id,
        payload=new_payload)
    return user_instances_enforced

@task(name="monitor_instance_allocations")
def monitor_instance_allocations():
    """
    Update instances for each active provider.
    """
    if settings.USE_ALLOCATION_SOURCE:
        celery_logger.info("Skipping the old method of monitoring instance allocations")
        return False
    for p in Provider.get_active():
        monitor_instances_for.apply_async(args=[p.id], kwargs={'check_allocations':True})


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
        console_handler = _init_stdout_logging()

    # DEVNOTE: Potential slowdown running multiple functions
    # Break this out when instance-caching is enabled
    running_total = 0
    if not settings.ENFORCING:
        celery_logger.debug('Settings dictate allocations are NOT enforced')
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
        _exit_stdout_logging(console_handler)
    return running_total


@task(name="monitor_volumes")
def monitor_volumes():
    """
    Update volumes for each active provider.
    """
    for p in Provider.get_active():
        monitor_volumes_for.apply_async(args=[p.id])

@task(name="monitor_volumes_for")
def monitor_volumes_for(provider_id, print_logs=False):
    """
    Run the set of tasks related to monitoring sizes for a provider.
    Optionally, provide a list of usernames to monitor
    While debugging, print_logs=True can be very helpful.
    start_date and end_date allow you to search a 'non-standard' window of time.
    """
    from service.driver import get_account_driver
    from core.models import Identity
    if print_logs:
        console_handler = _init_stdout_logging()

    provider = Provider.objects.get(id=provider_id)
    account_driver = get_account_driver(provider)
    # Non-End dated volumes on this provider
    db_volumes = Volume.objects.filter(only_current_source(), instance_source__provider=provider)
    all_volumes = account_driver.admin_driver.list_all_volumes(timeout=30)
    seen_volumes = []
    for cloud_volume in all_volumes:
        try:
            core_volume = convert_esh_volume(cloud_volume, provider_uuid=provider.uuid)
            seen_volumes.append(core_volume)
        except ObjectDoesNotExist:
            tenant_id = cloud_volume.extra['object']['os-vol-tenant-attr:tenant_id']
            tenant = account_driver.get_project_by_id(tenant_id)
            try:
                identity = Identity.objects.get(
                    provider=provider, created_by__username=tenant.name)
                core_volume = convert_esh_volume(
                    cloud_volume,
                    provider.uuid, identity.uuid,
                    identity.created_by)
            except ObjectDoesNotExist:
                celery_logger.info("Skipping Volume %s - Unknown Identity: %s-%s" % (cloud_volume.id, provider, tenant.name))
            pass

    now_time = timezone.now()
    needs_end_date = [volume for volume in db_volumes if volume not in seen_volumes]
    for volume in needs_end_date:
        celery_logger.debug("End dating inactive volume: %s" % volume)
        volume.end_date = now_time
        volume.save()

    if print_logs:
        _exit_stdout_logging(console_handler)


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
        console_handler = _init_stdout_logging()

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
        _exit_stdout_logging(console_handler)


@task(name="monthly_allocation_reset")
def monthly_allocation_reset():
    """
    This task contains logic related to:
    * Providers whose allocations should be reset on the first of the month
    * Which Allocation will be used as 'default'
    """
    default_allocation = Allocation.default_allocation()
    provider_locations = None
    # ensure a 'set' settings value
    if hasattr(settings, 'MONTHLY_RESET_PROVIDER_LOCATIONS'):
        provider_locations = settings.MONTHLY_RESET_PROVIDER_LOCATIONS
    else:
        raise Exception("settings.MONTHLY_RESET_PROVIDER_LOCATIONS has not been set. SKIPPING the monthly allocation reset.")

    # Ensure settings value is a list
    if not provider_locations or not isinstance(provider_locations, list):
        raise Exception("Expected a list ([]) of provider locations to receive a monthly reset")
    for location in provider_locations:
        provider = Provider.objects.get(location=location)
        reset_provider_allocation.apply_async(
            args=[
                provider.id,
                default_allocation.id])
    return


@task(name="reset_provider_allocation")
def reset_provider_allocation(provider_id, default_allocation_id):
    default_allocation = Allocation.objects.get(id=default_allocation_id)
    this_provider = Q(identity__provider_id=provider_id)
    no_privilege = (Q(identity__created_by__is_staff=False) &
                   Q(identity__created_by__is_superuser=False))
    expiring_allocation = ~Q(allocation__delta=-1)
    members = IdentityMembership.objects.filter(
        this_provider,
        no_privilege,
        expiring_allocation)
    num_reset = members.update(allocation=default_allocation)
    return num_reset

def _end_date_missing_database_machines(db_machines, cloud_machines, now=None, dry_run=False):
    if not now:
        now = timezone.now()
    mach_count = 0
    cloud_machine_ids = [mach.id for mach in cloud_machines]
    for machine in db_machines:
        cloud_match = [mach for mach in cloud_machine_ids if mach == machine.identifier]
        if not cloud_match:
            remove_machine(machine, now, dry_run=dry_run)
            mach_count += 1
    return mach_count


def _remove_versions_without_machines(now=None):
    if not now:
        now = timezone.now()
    ver_count = 0
    versions_without_machines = ApplicationVersion.objects.filter(
        machines__isnull=True, end_date__isnull=True)
    ver_count = _perform_end_date(versions_without_machines, now)
    return ver_count


def _remove_applications_without_versions(now=None):
    if not now:
        now = timezone.now()
    app_count = 0
    apps_without_versions = Application.objects.filter(
        versions__isnull=True, end_date__isnull=True)
    app_count = _perform_end_date(apps_without_versions, now)
    return app_count


def _update_improperly_enddated_applications(now=None):
    if not now:
        now = timezone.now()
    improperly_enddated_apps = Application.objects.annotate(
        num_versions=Count('versions'), num_machines=Count('versions__machines')
    ).filter(
        inactive_versions(),
        # AND application has already been end-dated.
        end_date__isnull=False
    )
    app_count = _perform_end_date(improperly_enddated_apps, now)
    return app_count


def _perform_end_date(queryset, end_dated_at):
    count = 0
    for model in queryset:
        model.end_date_all(end_dated_at)
        count += 1
    return count


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
    cloud_machine_is_public = cloud_machine.is_public if hasattr(cloud_machine,'is_public') else cloud_machine.get('visibility','') == 'public'
    if cloud_machine_is_public == True:
        celery_logger.info("Making Machine %s private" % cloud_machine.id)
        account_driver.image_manager.glance.images.update(cloud_machine.id, visibility='private')

    celery_logger.info("Sharing image %s<%s>: %s with %s" % (cloud_machine.id, cloud_machine.name, identity.provider.location, tenant_name.value))
    if not dry_run:
        try:
            account_driver.image_manager.share_image(cloud_machine, tenant_name.value)
        except GlanceConflict as exc:
            if 'already associated with image' in exc.message:
                pass
        except GlanceForbidden as exc:
            if 'Public images do not have members' in exc.message:
                celery_logger.warn("CONFLICT -- This image should have been marked 'private'! %s" % cloud_machine)
                pass
    return

def _exit_stdout_logging(consolehandler):
    celery_logger.removeHandler(consolehandler)

def _init_stdout_logging(logger=None):
    if not logger:
        logger = celery_logger
    import logging
    import sys
    consolehandler = logging.StreamHandler(sys.stdout)
    consolehandler.setLevel(logging.DEBUG)
    logger.addHandler(consolehandler)
    return consolehandler
