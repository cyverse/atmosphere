#!/usr/bin/env python
import argparse
import json
import sys

import os
import django
django.setup()
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
import libcloud.security


root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.environ["DJANGO_SETTINGS_MODULE"] = "atmosphere.settings"
sys.path.insert(1, root_dir)
django.setup()

from core.models import Provider, PlatformType, ProviderType, Identity, Group,\
    IdentityMembership, AccountProvider, Quota, ProviderInstanceAction
from core.models import InstanceAction

libcloud.security.VERIFY_SSL_CERT = False
libcloud.security.VERIFY_SSL_CERT_STRICT = False
KVM = PlatformType.objects.get_or_create(name='KVM')[0]
XEN = PlatformType.objects.get_or_create(name='Xen')[0]
openstack = ProviderType.objects.get(name='OpenStack')
eucalyptus = ProviderType.objects.get(name='Eucalyptus')

valid_url = URLValidator()


def get_valid_url(raw_url):
    try:
        valid_url(raw_url)
        return raw_url
    except ValidationError:
        print "The url specified was invalid."


def has_fields(fields, required_fields):
    for field in required_fields:
        if field not in fields:
            print "The required field `%s` was not found." % field
            return False
    return True


def read_provider_info(filename):
    data = None

    with open(filename) as fp:
        data = fp.read()

    # Require the file to contain content
    if not data:
        print("Please specify a non-empty json file.")
        sys.exit(1)

    # Load data as json
    try:
        info = json.loads(data)
    except:
        print("Invalid file format expected a json file.")
        sys.exit(1)

    provider_info = info["provider"]
    admin_info = info["admin"]
    credential_info = info["credential"]

    return provider_info, admin_info, credential_info


def get_provider_info():
    # 1.  Collect name
    print "What is the name of your new provider?"
    name = raw_input("Name of new provider: ")
    # 2.  Collect platform type
    print "Select a platform type for your new provider"
    print "1: KVM, 2: Xen"
    while True:
        platform = raw_input("Select a platform type (1/2): ")
        if platform == '1':
            platform = KVM
            break
        elif platform == '2':
            platform = XEN
            break

    # 3.  Collect provider type
    print "Select a provider type for your new provider"
    print "1: Openstack, 2: Eucalyptus"
    while True:
        provider_type = raw_input("Select a provider type (1/2): ")
        if provider_type == '1':
            provider_type = openstack
            break
        elif provider_type == '2':
            provider_type = eucalyptus
            break

    return {
        "name": name,
        "platform": platform,
        "type": provider_type
    }


def get_admin_info():
    print "What is the username of the provider admin?"
    username = raw_input("username of provider admin: ")

    print "What is the password of the provider admin?"
    password = raw_input("password of provider admin: ")

    print "What is the tenant_name of the provider admin?"
    tenant = raw_input("tenant_name of provider admin: ")
    return {
        "username": username,
        "password": password,
        "tenant": tenant
    }


def get_provider_credentials():
    admin_url = None
    auth_url = None

    print "What is the admin_url for the provider?"
    while not admin_url:
        raw_url = raw_input("admin_url for the provider: ")
        admin_url = get_valid_url(raw_url)

    print "What is the auth_url for the provider?"
    while not auth_url:
        raw_url = raw_input("auth_url for the provider: ")
        auth_url = get_valid_url(raw_url)

    print "What is the router_name for the provider?"
    router_name = raw_input("router_name for the provider: ")

    print "What is the region_name for the provider?"
    region_name = raw_input("region_name for the provider: ")

    return {
        "admin_url": admin_url,
        "auth_url": auth_url,
        "router_name": router_name,
        "region_name": region_name
    }


def create_admin(provider, admin_info):
    REQUIRED_FIELDS = ["username", "password", "tenant"]

    if not has_fields(admin_info, REQUIRED_FIELDS):
        print "Please add missing admin information."
        sys.exit(1)

    username = admin_info["username"]
    password = admin_info["password"]
    tenant = admin_info["tenant"]

    (user, group) = Group.create_usergroup(username)

    new_identity = Identity.objects.get_or_create(provider=provider,
                                                  created_by=user)[0]
    new_identity.credential_set.get_or_create(key='key',
                                              value=username)
    new_identity.credential_set.get_or_create(key='secret',
                                              value=password)
    new_identity.credential_set.get_or_create(key='ex_tenant_name',
                                              value=tenant)
    new_identity.credential_set.get_or_create(key='ex_project_name',
                                              value=tenant)

    quota = Quota.objects.filter(**Quota.default_dict()).first()
    if not quota:
        quota = Quota.default_quota()
    # TODO: Test why we do this here and not AFTER creating AccountProvider/IdentityMembership -- Then label the rationale.
    # Necessary for save hooks -- Default project, select an identity
    user.save()

    AccountProvider.objects.get_or_create(
        provider=provider, identity=new_identity)
    IdentityMembership.objects.get_or_create(
        identity=new_identity, member=group, quota=quota)

    return new_identity


def create_provider(provider_info):
    REQUIRED_FIELDS = ["name", "platform", "type"]

    if not has_fields(provider_info, REQUIRED_FIELDS):
        print "Please add missing provider information."
        sys.exit(1)

    try:
        provider = Provider.objects.get(location=provider_info["name"])
        print "Found existing provider with name %s: %s"\
            % (provider_info["name"], provider)
        return provider
    except Provider.DoesNotExist:
        pass

    new_provider = Provider.objects.create(
        location=provider_info["name"],
        virtualization=provider_info["platform"],
        type=provider_info["type"], public=False)
    # 3b. Associate all InstanceActions
    instance_actions = InstanceAction.objects.all()
    for action in instance_actions:
        ProviderInstanceAction.objects.get_or_create(
            provider=new_provider,
            instance_action=action,
            enabled=True)
    # 4.  Create a new provider
    print "Created a new provider: %s" % (new_provider.location)
    return new_provider


def create_provider_credentials(provider, credential_info):
    REQUIRED_FIELDS = ["admin_url", "auth_url", "router_name", "region_name"]

    if not has_fields(credential_info, REQUIRED_FIELDS):
        print "Please add missing credential information."
        sys.exit(1)

    for (key, value) in credential_info.items():
        provider.providercredential_set.get_or_create(key=key, value=value)


def main():
    parser = argparse.ArgumentParser(
        description="Add a new cloud provider and adminstrator")

    parser.add_argument("--from-json", dest="json",
                        help="Add a new provider for a json file.")

    arguments = parser.parse_args()

    if arguments.json:
        (provider_info,
         admin_info,
         provider_credentials) = read_provider_info(arguments.json)
    else:
        provider_info = get_provider_info()
        admin_info = get_admin_info()
        provider_credentials = get_provider_credentials()

    new_provider = create_provider(provider_info)
    create_provider_credentials(new_provider, provider_credentials)
    create_admin(new_provider, admin_info)
    print "You still need to create an AllocationStrategy. Go into the admin panel and select a Strategy *BEFORE* you use Atmosphere"

if __name__ == "__main__":
    main()
