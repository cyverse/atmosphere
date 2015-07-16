from core.models import Provider, ProviderMachine, Identity, UserProfile
import re

import django
django.setup()


def retrieve_euca_owners(self, orm):
    print 'Parsing existing eucalyptus machines for owners'
    euca_providers = Provider.objects.filter(location='EUCALYPTUS')
    for prov in euca_providers:
        admin_id = self.get_admin_identity(orm, prov)
        driver = self.get_esh_driver(admin_id)
        for machine in driver.list_machines():
            try:
                location = machine._image.extra['location']
                owner = parse_location(location)
                owner_id = Identity.objects.get(
                    created_by__username=owner,
                    provider=prov)
                pm = ProviderMachine.objects.filter(identifier=machine.id)
                if not pm:
                    continue
                print 'Updating %s - created by %s' % (machine.id, owner)
                pm = pm[0]
                pm.created_by = owner_id.created_by
                pm.created_by_identity = owner_id
                pm.save()
                app = pm.application
                # TODO: Not necessarily true, look this over before you run it
                # again..
                app.created_by = owner_id.created_by
                app.created_by_identity = owner_id
                app.save()
            except Identity.DoesNotExist:
                print 'Cannot rename machine %s, owner %s does not exist' %\
                    (machine, owner)


def parse_location(location):
    bucket, image = location.split('/')
    bucket_regex = re.compile("(?P<admin_tag>[^_]+)_(?P<owner_name>[^_]+).*$")
    image_regex = re.compile(
        "(?P<admin_or_owner>[^_]+)_(?P<owner_name>[^_]+).*$")
    r = bucket_regex.search(bucket)
    if not r:
        # Non-standard bucket location.. Skip it
        return
    search_results = r.groupdict()
    owner_name = search_results['owner_name']
    if owner_name not in [
            'admin',
            'mi'] and UserProfile.objects.filter(
            user__username=owner_name):  # username found on bucket
        user_found = owner_name
    else:
        # Check the image name
        r = image_regex.search(image)
        if not r:
            # Non-standard image location.. Skip it
            return
        search_results = r.groupdict()
        owner_name = search_results['owner_name']
        if owner_name not in [
                'admin',
                'mi'] and UserProfile.objects.filter(
                user__username=owner_name):  # username found on image
            user_found = owner_name
        else:
            user_found = search_results['admin_or_owner']
    print 'Location parsing %s found owner %s' % (location, owner)
    return user_found
