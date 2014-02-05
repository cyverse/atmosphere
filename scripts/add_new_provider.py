#!/usr/bin/env python
import libcloud.security

from core.models import Provider, PlatformType, ProviderType, Identity, Group,\
    ProviderMembership, IdentityMembership, AccountProvider, Quota

libcloud.security.VERIFY_SSL_CERT = False
libcloud.security.VERIFY_SSL_CERT_STRICT = False
KVM = PlatformType.objects.get_or_create(name='KVM')[0]
XEN = PlatformType.objects.get_or_create(name='Xen')[0]
openstack = ProviderType.objects.get(name='OpenStack')
eucalyptus = ProviderType.objects.get(name='Eucalyptus')


def main():
    new_provider = create_provider()
    new_admin = create_admin(new_provider)


def create_admin(provider):
    print "What is the username of the provider admin?"
    username_select = raw_input("username of provider admin: ")
    print "What is the password of the provider admin?"
    password_select = raw_input("password of provider admin: ")
    print "What is the tenant_name of the provider admin?"
    tenant_name_select = raw_input("tenant_name of provider admin: ")

    print "What is the admin_url of the provider admin?"
    admin_url_select = raw_input("admin_url of provider admin: ")
    print "What is the auth_url of the provider admin?"
    auth_url_select = raw_input("auth_url of provider admin: ")
    print "What is the router_name of the provider admin?"
    router_name_select = raw_input("router_name of provider admin: ")
    print "What is the region_name of the provider admin?"
    region_name_select = raw_input("region_name of provider admin: ")

    (user, group) = Group.create_usergroup(username_select)

    new_identity = Identity.objects.get_or_create(provider=provider,
                                                  created_by=user)[0]
    new_identity.credential_set.get_or_create(key='key',
                                              value=username_select)
    new_identity.credential_set.get_or_create(key='secret',
                                              value=password_select)
    new_identity.credential_set.get_or_create(key='ex_tenant_name',
                                              value=tenant_name_select)
    new_identity.credential_set.get_or_create(key='ex_project_name',
                                              value=tenant_name_select)
    provider.providercredential_set.get_or_create(key='admin_url',
                                                  value=admin_url_select)
    provider.providercredential_set.get_or_create(key='auth_url',
                                                  value=auth_url_select)
    provider.providercredential_set.get_or_create(key='router_name',
                                                  value=router_name_select)
    provider.providercredential_set.get_or_create(key='region_name',
                                                  value=region_name_select)

    prov_membership = ProviderMembership.objects.get_or_create(
        provider=provider, member=group)[0]
    quota = Quota.objects.all()[0]
    user.save()
    admin = AccountProvider.objects.get_or_create(
        provider=provider, identity=new_identity)[0]
    id_membership = IdentityMembership.objects.get_or_create(
        identity=new_identity, member=group, quota=quota)[0]
    return new_identity


def create_provider():
    #1.  Collect name
    print "What is the name of your new provider?"
    name_select = raw_input("Name of new provider: ")
    provider = Provider.objects.filter(location=name_select)
    if provider:
        print "Found existing provider with name %s: %s"\
            % (name_select, provider[0])
        return provider[0]
    #2.  Collect platform type
    print "Select a platform type for your new provider"
    print "1: KVM, 2: Xen"
    while True:
        platform_select = raw_input("Select a platform type (1/2): ")
        if platform_select == '1':
            platform = KVM
            break
        elif platform_select == '2':
            platform = XEN
            break

    #3.  Collect provider type
    print "Select a provider type for your new provider"
    print "1: Openstack, 2: Eucalyptus"
    while True:
        provider_select = raw_input("Select a provider type (1/2): ")
        if provider_select == '1':
            provider = openstack
            break
        elif provider_select == '2':
            provider = eucalyptus
            break
    new_provider = Provider.objects.create(location=name_select,
                                           virtualization=platform,
                                           type=provider,
                                           public=False)
    #4.  Create a new provider
    print "Created a new provider: %s" % (new_provider.location)
    return new_provider

if __name__ == "__main__":
    main()
