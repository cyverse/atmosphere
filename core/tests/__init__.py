from core.tests.instance import *
from atmosphere import settings
from core.models import ProviderCredential, ProviderType, Provider, Identity

def create_euca_provider():
    provider_type = ProviderType.objects.get_or_create(name='Eucalyptus')[0]
    euca = Provider.objects.get_or_create(location='EUCALYPTUS',
                                          type=provider_type)[0]
    ProviderCredential.objects.get_or_create(
        key='ec2_url', value=settings.EUCA_EC2_URL, provider=euca)
    ProviderCredential.objects.get_or_create(
        key='s3_url', value=settings.EUCA_S3_URL, provider=euca)
    ProviderCredential.objects.get_or_create(
        key='euca_cert_path', value=settings.EUCALYPTUS_CERT_PATH,
         provider=euca)
    ProviderCredential.objects.get_or_create(
        key='pk_path', value=settings.EUCA_PRIVATE_KEY,
         provider=euca)
    ProviderCredential.objects.get_or_create(
        key='ec2_cert_path', value=settings.EC2_CERT_PATH,
         provider=euca)
    ProviderCredential.objects.get_or_create(
        key='account_path', value='/services/Accounts',
         provider=euca)
    ProviderCredential.objects.get_or_create(
        key='config_path', value='/services/Configuration',
         provider=euca)
    identity = Identity.create_identity('admin', euca.location,
        account_admin=True,
        cred_key=settings.EUCA_ADMIN_KEY,
        cred_secret=settings.EUCA_ADMIN_SECRET)
    return identity

def create_os_provider():
    provider_type = ProviderType.objects.get_or_create(name='OpenStack')[0]
    openstack = Provider.objects.get_or_create(
            location='OPENSTACK',
            type=provider_type)[0]
    ProviderCredential.objects.get_or_create(key='auth_url',
            value=settings.OPENSTACK_AUTH_URL, provider=openstack)
    ProviderCredential.objects.get_or_create(key='admin_url',
            value=settings.OPENSTACK_ADMIN_URL, provider=openstack)
    ProviderCredential.objects.get_or_create(key='router_name',
            value=settings.OPENSTACK_DEFAULT_ROUTER, provider=openstack)
    ProviderCredential.objects.get_or_create(key='region_name',
            value=settings.OPENSTACK_DEFAULT_REGION, provider=openstack)
    identity = Identity.create_identity(
        settings.OPENSTACK_ARGS['username'],
        openstack.location, account_admin=True,
        cred_key=settings.OPENSTACK_ADMIN_KEY,
        cred_secret=settings.OPENSTACK_ADMIN_SECRET,
        cred_ex_tenant_name=settings.OPENSTACK_ADMIN_TENANT,
        cred_ex_project_name=settings.OPENSTACK_ADMIN_TENANT)
    return identity
