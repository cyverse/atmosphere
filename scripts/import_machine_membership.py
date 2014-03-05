#!/usr/bin/env python
from core.models import MachineRequest, Provider, ProviderMachine,\
        ProviderMachineMembership, Group
from core.models.credential import get_groups_using_credential
from core.models.machine_request import process_machine_request,\
        sync_image_access_list
from service.accounts.openstack import AccountDriver as OSAccounts
from service.driver import get_admin_driver
from api.machine import list_filtered_machines
from django.db.models import Q
from django.utils import timezone
import json

def write_membership(group, pm):
    obj, created = ProviderMachineMembership.objects.get_or_create(
            group=group, 
            provider_machine=pm)
    if created:
        print "Created new ProviderMachineMembership: %s-%s" \
            % (pm.identifier, group.name)

def make_public(image_manager, image, provider_machine):
    if image.is_public == False:
        image_manager.update_image(image, is_public=True)
    if provider_machine.application.private == True:
        provider_machine.application.private = False
        provider_machine.application.save()


def make_private(image_manager, image, provider_machine, tenant_list=[]):
    if image.is_public == True:
        print "Marking image %s private" % image.id
        image_manager.update_image(image, is_public=False)
    if provider_machine.application.private == False:
        print "Marking application %s private" % provider_machine.application
        provider_machine.application.private = True
        provider_machine.application.save()
    #Add all these people by default..
    owner = provider_machine.application.created_by
    group_list = owner.group_set.all()
    if tenant_list:
        for tenant in tenant_list:
            name = tenant.name
            group = Group.objects.get(name=name)
            write_membership(group, provider_machine)

def main():
    for prov in Provider.objects.filter(type__name__icontains='openstack'):
        if not prov.is_active():
            continue
        print "Importing machine membership for %s" % prov
        accounts = OSAccounts(prov)
        if not accounts:
            print "Aborting import: Could not retrieve OSAccounts driver "\
                    "for Provider %s" % prov
            continue
        admin_driver = get_admin_driver(prov)
        if not admin_driver:
            print "Aborting import: Could not retrieve admin_driver "\
                    "for Provider %s" % prov
            continue

        private_images = admin_driver.filter_machines(
                accounts.list_all_images(is_public=False),
                black_list=["eki-", "eri-", "ChromoSnapShot"])

        public_images = admin_driver.filter_machines(
                accounts.list_all_images(is_public=True),
                black_list=["eki-", "eri-", "ChromoSnapShot"])

        fix_public_images(public_images, prov, accounts)
        fix_private_images(private_images, prov, accounts)
        fix_private_images_without_repr(private_images, prov, accounts)

def parse_list(raw_access_list, provider_id):
    if '[' not in raw_access_list:
        #Format = "test1, test2, test3"
        json_loads_list = str(raw_access_list.split(", "))
        #New Format = "[u'test1', u'test2', u'test3']"
    else:
        #Format = "[u'test1', u'test2', u'test3']"
        json_loads_list = raw_access_list
    json_loads_list = json_loads_list.replace("'",'"').replace('u"', '"')
    user_list = json.loads(json_loads_list)
    return user_list

def fix_private_images_without_repr(private_images, prov, accounts):
    """
    See if image has a machine request
    See if we can 'piece it together'
    """
    for img in private_images:
        machine_requests = MachineRequest.objects.filter(
                new_machine_provider=prov,
                new_machine_name=img.name)
        for mr in machine_requests:
            print "Machine Request found matching name %s of image %s" \
                    % (img.name, img.id)
            if mr.status != 'completed':
                print "Processing machine with image %s" % img.id
                process_machine_request(mr, img.id)
            pm = mr.new_machine
            if mr.new_machine_visibility.lower() == 'public':
                make_public(accounts.image_manager, img, pm)
                continue
            #Private or selected access..
            access_list  = parse_list(mr.access_list, prov.id)
            #Fix on the image
            tenant_list = sync_image_access_list(
                    accounts, img, names=access_list)
            #Fix on the database
            make_private(accounts.image_manager, img, pm, tenant_list)


def fix_private_images(private_images, prov, accounts):
    """
    Potential problems with private images:
    * 1. MachineRequest contains this image and has more users on access_list
      Solution: add users on access_list to the image, update PMs and APPs
    * 2. Image has 0/1 user and is marked private
      Solution: Probably hidden on purpose.. Leave it there
    """
    image_total = len(private_images)
    print "Checking %s private images to see if they should be 'private' in openstack: %s"\
            % (image_total, prov)
    for idx, img in enumerate(private_images):
        #Check if this image has any 'shared users'
        pm = ProviderMachine.objects.filter(identifier=img.id,
                provider=prov)
        if not pm:
            continue
        pm = pm[0]
        machine_requests = MachineRequest.objects.filter(new_machine=pm)
        for mr in machine_requests:
            if mr.new_machine_visibility.lower() == 'public':
                print "Machine Request says image %s should be public" % img.id
                make_public(accounts.image_manager, img, pm)
                continue
            #Private or selected access..
            access_list  = parse_list(mr.access_list, prov.id)
            #Fix on the image
            tenant_list = sync_image_access_list(
                    accounts, img, names=access_list)
            #Fix on the database
            make_private(accounts.image_manager, img, pm, tenant_list)
        if not machine_requests:
            if pm.application.private == True:
                print "Application says %s<%s> should be private" % (img.name, img.id)
                make_private(accounts.image_manager, img, pm)
        if (idx % 5 == 0):
            print "Processed %s of %s machines" % (idx + 1, image_total)

def fix_public_images(public_images, prov, accounts):
    """
    Potential problems with public images:
    * 1. Openstack shows public and has users listed as 'image_members'
      Solution: mark image as private, and then update PMs and APPs
    * 2. MachineRequest shows this public image should be private
      Solution: mark image as private, share image with everyone in access list
    """
    image_total = len(public_images)
    print "Checking %s public images to see if they should be 'private' in openstack: %s"\
            % (image_total, prov)
    for idx, img in enumerate(public_images):
        #Check if this image has any 'shared users'
        pm = ProviderMachine.objects.filter(identifier=img.id,
                provider=prov)
        if not pm:
            continue
        pm = pm[0]
        machine_requests = MachineRequest.objects.filter(
                Q(new_machine=pm) &
                ~Q(new_machine_visibility__exact="public"))
        for mr in machine_requests:
            access_list  = parse_list(mr.access_list, prov.id)
            #Fix on the image
            print "Syncing image access list for %s<%s>" % (img.name, img.id)
            tenant_list = sync_image_access_list(
                    accounts, img, names=access_list)
            #Fix on the database
            print "Syncing database models for %s<%s>" % (img.name, img.id)
            make_private(accounts.image_manager, img, pm, tenant_list)
        if (idx % 5 == 0):
            print "Processed %s of %s machines" % (idx + 1, image_total)

if __name__ == "__main__":
    main()
