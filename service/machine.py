# -*- coding: utf-8 -*-
"""
Service layer for managing machines
"""
from functools import reduce
import operator

from threepio import logger

from core import models
from core.query import only_current_source
from service.cache import get_cached_driver
from service.driver import get_account_driver
from core.models.application import create_application, update_application
from core.models.application_version import create_app_version
from core.models.machine import (
    create_provider_machine,
    provider_machine_write_hook,
    update_provider_machine
)
from django.db.models import Q

def _get_owner(new_provider, user):
    try:
        return models.Identity.objects.get(provider=new_provider,
                                           created_by=user)
    except models.Identity.DoesNotExist:
        return new_provider.admin


def _match_tags_to_names(tag_names):
    """
    INPUT: tag1,tag2,tag3
    OUTPUT: <Tag: tag1>, ..., <Tag: tag3>
    NOTE: Tags NOT created BEFORE being added to new_machine_tags are ignored.
    """
    matches = [Q(name__iexact=name.strip()) for name in tag_names.split(',')]
    filters = reduce(operator.or_, matches, Q())
    return models.Tag.objects.filter(filters)


def remove_duplicate_users(user_list):
    users_dict = {}
    to_return = []

    for user in user_list:
        # remove blanks
        if user and user not in users_dict:
            users_dict[user] = True

    for user in users_dict.keys():
        to_return.append(str(user))

    return to_return


def process_machine_request(machine_request, new_image_id, update_cloud=True):
    """
    NOTE: Current process accepts instance with source of 'Image' ONLY!
          VOLUMES CANNOT BE IMAGED until this function is updated!
    """
    # Based on original instance -- You'll need this:
    parent_mach = machine_request.instance.provider_machine
    parent_version = parent_mach.application_version
    # Based on data provided in MR:
    new_provider = machine_request.new_machine_provider
    new_owner = machine_request.new_machine_owner
    owner_identity = _get_owner(new_provider, new_owner)
    tags = _match_tags_to_names(machine_request.new_version_tags)
    # TODO: Use it or remove it
    # membership = _match_membership_to_access(
    #     machine_request.access_list,
    #     machine_request.new_version_membership)
    if machine_request.new_version_forked:
        application = create_application(
            new_provider.uuid,
            new_image_id,
            machine_request.new_application_name,
            created_by_identity=owner_identity,
            description=machine_request.new_application_description,
            private=not machine_request.is_public(),
            tags=tags)
    else:
        application = update_application(
            parent_version.application,
            machine_request.new_application_name,
            tags,
            machine_request.new_application_description)
    #FIXME: Either *add* system_files here, or *remove* the entire field.
    app_version = create_app_version(
        application, machine_request.new_version_name,
        new_owner, owner_identity, machine_request.new_version_change_log,
        machine_request.new_version_allow_imaging,
        provider_machine_id=new_image_id)

    # 2. Create the new InstanceSource and appropriate Object, relations,
    # Memberships..
    if models.ProviderMachine.test_existence(new_provider, new_image_id):
        pm = models.ProviderMachine.objects.get(
            instance_source__identifier=new_image_id,
            instance_source__provider=new_provider)
        pm = update_provider_machine(
            pm,
            new_created_by_identity=owner_identity,
            new_created_by=machine_request.new_machine_owner,
            new_application_version=app_version)
    else:
        pm = create_provider_machine(new_image_id, new_provider.uuid,
                                     application, owner_identity, app_version)
        provider_machine_write_hook(pm)

    # Must be set in order to ask for threshold information
    machine_request.new_application_version = app_version
    machine_request.new_machine = pm
    machine_request.save()

    # 3. Associate additional attributes to new application
    if machine_request.has_threshold():
        machine_request.update_threshold()

    # 4a. Add new *Memberships For new ProviderMachine//Application
    if not machine_request.is_public():
        upload_privacy_data(machine_request, pm)

    # 4b. If new boot scripts have been associated,
    # add them to the new version.
    if machine_request.new_version_scripts.count():
        for script in machine_request.new_version_scripts.all():
            app_version.boot_scripts.add(script)

    # 4c. If new licenses have been associated, add them to the new version.
    if machine_request.new_version_licenses.count():
        for license in machine_request.new_version_licenses.all():
            app_version.licenses.add(license)
    return machine_request


def update_machine_metadata(core_machine, data={}):
    identity = core_machine.created_by_identity
    machine_id = core_machine.provider_alias
    esh_driver = get_cached_driver(identity=identity)
    esh_machine = esh_driver.get_machine(machine_id)
    return _update_machine_metadata(esh_driver, esh_machine, data)


def _update_machine_metadata(esh_driver, esh_machine, data={}):
    """
    NOTE: This will NOT WORK for TAGS until openstack
    allows JSONArrays as values for metadata!
    """
    if not hasattr(esh_driver._connection, 'ex_set_image_metadata'):
        logger.info(
            "EshDriver %s does not have function 'ex_set_image_metadata'" %
            esh_driver._connection.__class__)
        return {}
    try:
        # Possible metadata that could be in 'data'
        #  * application uuid
        #  * application name
        #  * specific machine version
        # TAGS must be converted from list --> String
        logger.info("New metadata:%s" % data)
        meta_response = esh_driver._connection.ex_set_image_metadata(
            esh_machine,
            data)
        esh_machine.invalidate_machine_cache(esh_driver.provider, esh_machine)
        return meta_response
    except Exception as e:
        logger.exception("Error updating machine metadata")
        if 'incapable of performing the request' in e.message:
            return {}
        else:
            raise


def share_with_admins(private_userlist, provider_uuid):
    """
    NOTE: This will always work, but the userlist could get long some day.
    Another option would be to create an 'admin' tenant that all of core
    services and the admin are members of, and add only that tenant to the
    list.
    """
    if not isinstance(private_userlist, list):
        raise Exception("Expected private_userlist to be list, got %s: %s"
                        % (type(private_userlist), private_userlist))

    from django_cyverse_auth.protocol.ldap import get_core_services
    core_services = get_core_services()
    admin_users = [
        ap.identity.created_by.username
        for ap in models.AccountProvider.objects.filter(
            provider__uuid=provider_uuid)]
    private_userlist.extend(core_services)
    private_userlist.extend(admin_users)
    return private_userlist


def upload_privacy_data(machine_request, new_machine):
    """
    ASSERT: The image in 'new_machine' SHOULD BE private
    (Based on values in machine_request)
    """
    prov = new_machine.provider
    accounts = get_account_driver(prov)
    if not accounts:
        print "Aborting import: Could not retrieve Account Driver "\
            "for Provider %s" % prov
        return
    img = accounts.get_image(new_machine.identifier)
    if hasattr(img, 'visibility'):  # Treated as an obj.
        is_public = img.visibility == 'public'
    elif hasattr(img, 'items'):  # Treated as a dict.
        is_public = img.get('visibility','N/A') == 'public'

    if is_public:
        print "Marking image %s private" % img.id
        accounts.image_manager.update_image(img, visibility='private')

    accounts.clear_cache()
    admin_driver = accounts.admin_driver  # cache has been cleared
    if not admin_driver:
        print "Aborting import: Could not retrieve admin_driver "\
            "for Provider %s" % prov
        return
    img = accounts.get_image(new_machine.identifier)
    tenant_list = machine_request.get_access_list()
    # All in the list will be added as 'sharing' the OStack img
    # All tenants already sharing the OStack img will be added to this list
    return sync_machine_membership(accounts, img, new_machine, tenant_list)


def add_membership(image_version, group):
    """
    This function will add *all* users in the group
    to *all* providers/machines using this image_version
    O(N^2)
    """
    for provider_machine in image_version.machines.filter(only_current_source()):
        add_machine_membership(provider_machine, group)


def add_machine_membership(provider_machine, group):
    update_db_membership_for_group(provider_machine, group)
    update_cloud_membership_for_machine(provider_machine, group)


def update_cloud_membership_for_machine(provider_machine, group):
    """
    Given a provider_machine and a group
    * Loop through identities owned by group
    * * If identity.provider == provider_machine.provider, allow identity to launch via cloud ACLs
    """
    prov = provider_machine.instance_source.provider
    accounts = get_account_driver(prov)
    if not accounts:
        raise NotImplemented("Account Driver could not be created for %s" % prov)
    accounts.clear_cache()
    admin_driver = accounts.admin_driver  # cache has been cleared
    if not admin_driver:
        raise NotImplemented("Admin Driver could not be created for %s" % prov)
    img = accounts.get_image(provider_machine.identifier)
    projects = accounts.shared_images_for(img.id)
    for identity_membership in group.identitymembership_set.all():
        if identity_membership.identity.provider != prov:
            logger.debug("Skipped %s -- Wrong provider" % identity_membership.identity)
            continue
        # Get project name from the identity's credential-list
        project_name = identity_membership.identity.get_credential('ex_project_name')
        project = accounts.get_project(project_name)
        if project and project not in projects:
            logger.debug("Skipped Project: %s -- Already shared" % project)
            continue
        accounts.share_image_with_project(img, project_name)


def update_db_membership_for_group(provider_machine, group):
    # Share with the *database* first!
    obj, created = models.ApplicationMembership.objects.get_or_create(
        group=group,
        application=provider_machine.application)
    if created:
        logger.info("Created new ApplicationMembership: %s" \
            % (obj,))
    obj, created = models.ApplicationVersionMembership.objects.get_or_create(
        group=group,
        image_version=provider_machine.application_version)
    if created:
        logger.info("Created new ApplicationVersionMembership: %s" \
            % (obj,))
    obj, created = models.ProviderMachineMembership.objects.get_or_create(
        group=group,
        provider_machine=provider_machine)
    if created:
        logger.info("Created new ProviderMachineMembership: %s" \
            % (obj,))


def remove_membership(image_version, group):
    """
    This function will remove *all* users in the group
    to *all* providers/machines using this image_version
    """
    for provider_machine in image_version.machines.filter(only_current_source()):
        prov = provider_machine.instance_source.provider
        accounts = get_account_driver(prov)
        if not accounts:
            raise NotImplemented("Account Driver could not be created for %s" % prov)
        accounts.clear_cache()
        admin_driver = accounts.admin_driver  # cache has been cleared
        if not admin_driver:
            raise NotImplemented("Admin Driver could not be created for %s" % prov)
        img = accounts.get_image(provider_machine.identifier)
        projects = accounts.shared_images_for(img.id)
        for identity_membership in group.identitymembership_set.all():
            if identity_membership.identity.provider != prov:
                continue
            # Get project name from the identity's credential-list
            project_name = identity_membership.identity.get_credential(
                    'ex_project_name')
            project = accounts.get_project(project_name)
            if project and project not in projects:
                continue
            # Perform a *DATABASE* remove first.
            models.ApplicationMembership.objects.filter(
                group=group,
                application=provider_machine.application).delete()
            logger.info("Removed ApplicationMembership: %s-%s"
                        % (provider_machine.application, group))
            models.ApplicationVersionMembership.objects.filter(
                group=group,
                application_version=provider_machine.application_version).delete()
            logger.info("Removed ApplicationVersionMembership: %s-%s"
                        % (provider_machine.application_version, group))
            models.ProviderMachineMembership.objects.filter(
                group=group,
                provider_machine=provider_machine).delete()
            logger.info("Removed ProviderMachineMembership: %s-%s"
                        % (provider_machine, group))
            # Perform a *CLOUD* remove last.
            accounts.image_manager.unshare_image(img, project_name)
            logger.info("Removed Cloud Access: %s-%s"
                        % (img, project_name))
    return

def sync_machine_membership(accounts, glance_image, new_machine, tenant_list):
    """
    This function will check that *all* tenants in 'tenant_list'
     have been added to OpenStack and DB-level access controls
    """
    tenant_list = sync_cloud_access(accounts, glance_image, names=tenant_list)
    # Make private on the DB level
    make_private(accounts.image_manager,
                 glance_image, new_machine, tenant_list)


def sync_membership(accounts, glance_image, new_machine, tenant_list):
    return sync_machine_membership(accounts, glance_image, new_machine, tenant_list)


def share_with_self(private_userlist, username):
    if not isinstance(private_userlist, list):
        raise Exception(
            "Expected type(private_userlist) to be list, got %s: %s" %
            (type(private_userlist), private_userlist))

    # TODO: Optionally, Lookup username and get the Projectname
    private_userlist.append(str(username))
    return private_userlist

def sync_cloud_access(accounts, img, names=None):
    shared_with = accounts.image_manager.shared_images_for(
        image_id=img.id)
    # Find tenants who are marked as 'sharing' on openstack but not on DB
    # Or just in One-line..
    projects = accounts.shared_images_for(img.id)
    # Any names who aren't already on the image should be added
    # Find names who are marked as 'sharing' on DB but not on OpenStack
    for name in names:
        project = accounts.get_project(name)
        if project and project not in projects:
            print "Sharing image %s with project named %s" \
                % (img.id, name)
            accounts.image_manager.share_image(img, name)
            projects.append(project)
    return projects


def make_private(image_manager, image, provider_machine, tenant_list=[]):
    if provider_machine.application.private is False:
        print "Marking application %s private" % provider_machine.application
        provider_machine.application.private = True
        provider_machine.application.save()
    # Add all these people by default..
    owner = provider_machine.application.created_by
    group_list = owner.group_set.all()
    if tenant_list:
        # ASSERT: Groupnames == Usernames
        tenant_list.extend([group.name for group in group_list])
    else:
        tenant_list = [group.name for group in group_list]
    for tenant in tenant_list:
        if type(tenant) != unicode:
            name = tenant.name
        else:
            name = tenant
        try:
            group = models.Group.objects.get(name=name)
        except models.Group.DoesNotExist:
            logger.warn("Group %s does not exist - Skipped sharing" % name)
            pass

        obj, created = models.ApplicationMembership.objects.get_or_create(
            group=group,
            application=provider_machine.application)
        if created:
            print "Created new ApplicationMembership: %s" \
                % (obj,)
        obj, created = models.ProviderMachineMembership.objects.get_or_create(
            group=group,
            provider_machine=provider_machine)
        if created:
            print "Created new ProviderMachineMembership: %s" \
                % (obj,)
