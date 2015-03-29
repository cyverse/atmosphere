#!/usr/bin/env python
import argparse
import time

from service.driver import get_esh_driver
from core.models import ProviderMachine, Provider, Identity, Application, MachineRequest
from core.models.application import _generate_app_uuid
from service.driver import get_admin_driver, get_account_driver
from service.instance import suspend_instance

#Ghetto cache ftw
Count = 1
Images = []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-list", action="store_true",
                        help="List of provider names and IDs")
    parser.add_argument("--provider-id", type=int,
                        help="Atmosphere provider ID"
                        " to use when importing users.")
    args = parser.parse_args()
    if args.provider_list:
        print "ID\tName"
        for p in Provider.objects.all().order_by('id'):
            print "%d\t%s" % (p.id, p.location)
        return
    if not args.provider_id:
        print "ERROR: provider-id is required. To get a list of providers use"\
            " --provider-list"
        return
    provider = Provider.objects.get(id=args.provider_id)
    print "Provider Selected:%s" % provider
    accounts = get_account_driver(provider)
    global Images
    Images = accounts.image_manager.admin_list_images()
    app_dict = verify_applications(provider, accounts)
    for key, image_list in app_dict.items():
        print "%s\n---" % (key,)
        for image in image_list:
            print "%s" % image
        print "\n\n"

def get_image(accounts, image_id):
    global Images, Count
    if not Images:
        Images = accounts.image_manager.admin_list_images()
        Count += 1
    if Count > 1:
        raise Exception("Oh nooooo")
    found_images = [i for i in Images if i.id == image_id]
    if found_images:
        return found_images[0]
    return None



def verify_applications(provider, accounts, print_log=False):
    """
    """
    name_match=[]
    new_apps = []
    not_real_apps = []
    correct_apps = []
    incorrect_apps = []

    for pm in ProviderMachine.objects.filter(provider=provider):
        uuid = _generate_app_uuid(pm.identifier)
        if print_log:
            print "ProviderMachine: %s == UUID: %s" % (pm.identifier, uuid)
        apps = Application.objects.filter(uuid=uuid)
        if not apps:
            g_img = get_image(accounts, pm.identifier)
            if not g_img:
                if print_log:
                    print "DELETE: Image was deleted %s" % pm.identifier
                not_real_apps.append(pm)
                continue
            name = g_img.name
            if Application.objects.filter(name=name).count():
                apps_2 = Application.objects.filter(name=name)
                if apps_2[0] == pm.application:
                    if print_log:
                        print "OKAY: %s points to correct application by NAME: %s" % (pm.identifier, name)
                    name_match.append(pm)
                else:
                    if print_log or True:
                        print "ProviderMachine: %s points to %s , doesnt match Name:%s OR UUID:%s" % (pm, pm.application, name, uuid)
                    incorrect_apps.append(pm)
            else:
                if print_log:
                    print "Creating new application-%s and assigning to %s. Named %s based on glance image." % (uuid, pm.identifier, name)
                new_apps.append(pm)
        else:
            if apps[0] == pm.application:
                if print_log:
                    print "OKAY: %s points to correct application." % pm.identifier
                correct_apps.append(pm)
            else:
                if print_log or True:
                    print "Application for UUID:%s - %s exists but PM points to %s" % (uuid, apps[0], pm.application)
                incorrect_apps.append(pm)
    return {
      'Matched By Name': name_match,
      'Incorrect': incorrect_apps,
      'Created': new_apps,
      'Deleted': not_real_apps,
    }


if __name__ == "__main__":
    main()
