#!/usr/bin/env python
from core.models import Credential, Provider, \
        ProviderMachineMembership, ProviderMachine
from core.models.credential import get_groups_using_credential
from service.accounts.openstack import AccountDriver as OSAccounts
from service.driver import get_admin_driver
from api.machine import list_filtered_machines
def write_membership(group, pm):
    obj, created = ProviderMachineMembership.objects.get_or_create(
            group=group, 
            provider_machine=pm)
    if created:
        print "Created new ProviderMachineMembership: %s" % obj

def make_private(image, provider_machine):
    if provider_machine.application.private == True:
        print "Image %s already marked private" % image.id
    else:
        print "Marking image %s private." % image.id
        provider_machine.application.private = True
        provider_machine.application.save()
    owner = provider_machine.application.created_by
    return [write_membership(group, provider_machine) for group in owner.group_set.all()]

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
        images = admin_driver.filter_machines(accounts.list_all_images(),
                black_list=["eki-", "eri-", "ChromoSnapShot"])
        print "Checking for image membership on %s machines for provider %s"\
                % (len(images), prov)
        for idx, img in enumerate(images):
            #Check if this image has any 'shared users'
            if (idx % 5 == 0):
                print "Processed %s of %s machines" % (idx, len(images))
            pm = ProviderMachine.objects.filter(identifier=img.id,
                    provider=prov)
            if not pm:
                continue
            pm = pm[0]
            if not img.is_public:
                make_private(img, pm)
            shared_with = accounts.image_manager.shared_images_for(
                    image_id=img.id)
            if not shared_with:
                continue
            print "Image %s has %s member(s)" % (img.id, len(shared_with))
            if img.is_public == True:
                print "Image CONFLICT %s %s - Members & Public" \
                        % (img.id, img.name)
            for member in shared_with:
                #Retrieve the tenant from the database
                project = accounts.get_project_by_id(member.member_id)
                if not project:
                    #Retrieve the tenant from keystone.
                    print "Member id %s not found in keystone project list"\
                            % (member.member_id,)
                    continue

                #Is this tenant_name/project_name used as a credential for this provider?
                affected_membership = get_groups_using_credential(
                        "ex_project_name", project.name, prov)
                for affected_member in affected_membership:
                    write_membership(affected_member.member, pm)
if __name__ == "__main__":
    main()
