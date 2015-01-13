from core.tests.instance import *
from core.tests.machine_request import *
from atmosphere.settings import secrets
from core.models import PlatformType, ProviderType, ProviderCredential,\
                        Provider, Identity
from uuid import uuid4

def create_euca_provider():
    provider_type = ProviderType.objects.get_or_create(name='Eucalyptus')[0]
    platform_type = PlatformType.objects.get_or_create(name='Xen')[0]
    euca = Provider.objects.get_or_create(location='EUCALYPTUS',
                                          virtualization=platform_type,
                                          type=provider_type)[0]
    ProviderCredential.objects.get_or_create(
        key='ec2_url', value=secrets.EUCA_EC2_URL, provider=euca)
    ProviderCredential.objects.get_or_create(
        key='s3_url', value=secrets.EUCA_S3_URL, provider=euca)
    ProviderCredential.objects.get_or_create(
        key='euca_cert_path', value=secrets.EUCALYPTUS_CERT_PATH,
         provider=euca)
    ProviderCredential.objects.get_or_create(
        key='pk_path', value=secrets.EUCA_PRIVATE_KEY,
         provider=euca)
    ProviderCredential.objects.get_or_create(
        key='ec2_cert_path', value=secrets.EC2_CERT_PATH,
         provider=euca)
    ProviderCredential.objects.get_or_create(
        key='account_path', value='/services/Accounts',
         provider=euca)
    ProviderCredential.objects.get_or_create(
        key='config_path', value='/services/Configuration',
         provider=euca)
    identity = Identity.create_identity('admin', euca.location,
        account_admin=True,
        cred_key=secrets.EUCA_ADMIN_KEY,
        cred_secret=secrets.EUCA_ADMIN_SECRET)
    return identity

def create_os_provider():
    provider_type = ProviderType.objects.get_or_create(name='OpenStack')[0]
    platform_type = PlatformType.objects.get_or_create(name='KVM')[0]
    identities = []
    #TODO: Make platform_type a variable when we encounter a NON-KVM OStack..
    for provider in secrets.TEST_PROVIDERS['openstack']:
        try:
            os_provider = Provider.objects.get(
                virtualization=platform_type,
                type=provider_type,
                location=provider['label'])
        except Provider.DoesNotExist:
            os_provider = Provider.objects.create(
                virtualization=platform_type,
                type=provider_type, uuid=str(uuid4()),
                location=provider['label'])
        ProviderCredential.objects.get_or_create(key='auth_url',
                value=provider['auth_url'], provider=os_provider)
        ProviderCredential.objects.get_or_create(key='admin_url',
                value=provider['admin_url'], provider=os_provider)
        ProviderCredential.objects.get_or_create(key='router_name',
                value=provider['default_router'], provider=os_provider)
        ProviderCredential.objects.get_or_create(key='region_name',
                value=provider['default_region'], provider=os_provider)
        identity = Identity.create_identity(
            provider['key'], provider['label'],
            account_admin=True,
            cred_key=provider['key'], cred_secret=provider['secret'],
            cred_ex_tenant_name=provider['tenant_name'],
            cred_ex_project_name=provider['tenant_name'])
        identities.append(identity)
    return identities[0]
