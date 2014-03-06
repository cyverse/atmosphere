#!/usr/bin/env python
from chromogenic.migrate import migrate_image
from core.models import Provider, Identity, ProviderMachine
from service.accounts.openstack import AccountDriver as OSAccountDriver
from service.accounts.eucalyptus import AccountDriver as EucaAccountDriver

failed_imaes = [
# NOTE: Fails to complete when 'yum' is running
"emi-CC741A8B",
# could not determine latest ramdisk.. because no kvm kernel downloaded.
"emi-BA292148", "emi-654625E1", 
]
image_these = [
"emi-2E952CCE"
]
def start(images):
    print 'Initializing account drivers'
    euca_accounts = EucaAccountDriver(Provider.objects.get(id=1))
    euca_img_class = euca_accounts.image_manager.__class__
    euca_img_creds = euca_accounts.image_creds
    os_accounts = OSAccountDriver(Provider.objects.get(id=4))
    os_img_class = os_accounts.image_manager.__class__
    os_img_creds = os_accounts.image_creds
    migrate_args = {
            'download_dir':"/Storage",
            'image_id':None,
            'xen_to_kvm':True,
            }
    print 'Account drivers initialized'
    for mach_to_migrate in images:
        migrate_args['image_id'] = mach_to_migrate
        pm = ProviderMachine.objects.get(identifier=mach_to_migrate)
        migrate_args['image_name'] = pm.application.name
        print 'Migrating %s..' % mach_to_migrate
        # Lookup machine, set nme
        migrate_image(euca_img_class, euca_img_creds, os_img_class, os_img_creds,
                **migrate_args)

if __name__ == "__main__":
    start(image_these)
