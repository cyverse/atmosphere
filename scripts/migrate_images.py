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
#"emi-E7F8300F", "emi-F1F122E4", "emi-968E2F96", "emi-BE9C2D12", "emi-A33C2C8E",
##"emi-C6E5248C", "emi-A7321D22", "emi-F13821D0",
#"emi-F8C42B73", "emi-0B423174", "emi-99433292", "emi-9394226D", "emi-4A9B29D1",
#"emi-088720A6", "emi-3BA02651", "emi-6A1E30D5", "emi-B42A1FBE", "emi-586A2363",
#"emi-490420DC", "emi-79D424AF", "emi-115B27A4", "emi-F795292C", "emi-CFDA2927",
#"emi-46BC29ED", "emi-BE2319E0", "emi-C5BC222E", 
#"emi-BF842462",
#"emi-C1A02467", "emi-B4393131", "emi-D95721E0", "emi-CD542927", "emi-DD302C83",
#"emi-DDB52EE0", "emi-5B8F2377", "emi-896B2634", "emi-C09B2460", "emi-1CD52DA6",
#"emi-07092D61", "emi-F3A42505", "emi-821E2745", "emi-F1BC24FE", "emi-D0812935",
#"emi-484D219F", "emi-D3B22F44", "emi-746826E5", "emi-BCEA2112", "emi-47BB2669",
#"emi-CB8B2921", "emi-EA68274A", "emi-2F0222B1", "emi-77B821E5", "emi-0BEB20AD",
"emi-009234EA", 
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
