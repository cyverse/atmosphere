#!/usr/bin/env python
import argparse
import json
import pprint
import sys
import subprocess

import django; django.setup()
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
import libcloud.security

from urlparse import urlparse

from core.models import Provider, PlatformType, ProviderType, Identity, Group,\
    IdentityMembership, AccountProvider, Quota, ProviderInstanceAction
from core.models import InstanceAction

libcloud.security.VERIFY_SSL_CERT = False
libcloud.security.VERIFY_SSL_CERT_STRICT = False
KVM = PlatformType.objects.get_or_create(name='KVM')[0]
XEN = PlatformType.objects.get_or_create(name='Xen')[0]
openstack = ProviderType.objects.get_or_create(name='OpenStack')[0]

valid_url = URLValidator()


def require_input(question, validate_answer=None):
    try:
        while True:
            answer = raw_input(question)
            if not answer:
                print "ERROR: Cannot leave this answer blank!"
                continue
            if validate_answer and not validate_answer(answer):
                continue
            break
        return answer
    except (KeyboardInterrupt, EOFError):
        print "ERROR: Script has been cancelled."
        sys.exit(1)


def review_information(provider_info, admin_info, provider_credentials):
    """
    """
    print "1. Provider Information"
    pprint.pprint(provider_info)
    print "2. Admin Information"
    pprint.pprint(admin_info)
    print "3. Provider Credentials"
    pprint.pprint(provider_credentials)
    review_completed = raw_input("Does everything above look correct? [Yes]/No")
    if not review_completed or review_completed.lower() == 'yes':
        return
    while True:
        delete_section = raw_input("What section should be removed? 1, 2, 3, [exit]")
        if not delete_section or 'exit' in delete_section:
            break
        if '1' in delete_section:
            provider_info.clear()
            print "1. Provider Information deleted"
        if '2' in delete_section:
            admin_info.clear()
            print "2. Admin Information deleted"
        if '3' in delete_section:
            provider_credentials.clear()
            print "3. Provider Credentials deleted"


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


def read_json_file(filename):
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


def read_openrc_file(filename):
    command = ['bash', '-c', 'source %s && env' % filename]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE)
    output, err = proc.communicate()
    os_environ = {}
    for line in output.split('\n'):
        (key, _, value) = line.partition("=")
        if "OS_" in key:
            os_environ[key] = value
    if not os_environ:
        print("Please specify a non-empty openrc file.")
        sys.exit(1)
    parse_results = urlparse(os_environ['OS_AUTH_URL'])
    server_hostport = parse_results.port
    server_hostname = parse_results.netloc.replace(":"+str(server_hostport), '')
    server_scheme = parse_results.scheme
    provider_info = {
        "name": None,
        "platform": None,
        "type": openstack,
    }
    admin_info = {
        "username": os_environ["OS_USERNAME"],
        "tenant": os_environ["OS_TENANT_NAME"],
        "password": os_environ["OS_PASSWORD"],
        }
    credential_info = {
        "admin_url": "%s://%s:%s" % (server_scheme, server_hostname, "35357"),
        "auth_url": "%s://%s:%s" % (server_scheme, server_hostname, "5000"),
        "ex_force_auth_version": "2.0_password" if '/v2.0' in parse_results.path else '3.x_password',
        "router_name": None,
        "region_name": os_environ["OS_REGION_NAME"]
    }
    return provider_info, admin_info, credential_info


def get_provider_info(provider_info={}):
    # 1.  Collect name
    if not provider_info.get('name'):
        print "What is the name of your new provider?"
        provider_info['name'] = require_input("Name of new provider: ")
    # 2.  Collect platform type
    if not provider_info.get('platform'):
        print "Select a platform type for your new provider"
        print "1: KVM, 2: Xen"
        platform = require_input("Select a platform type (1/2): ", lambda answer: answer in ['1','2'])
        if platform == '1':
            platform = KVM
        elif platform == '2':
            platform = XEN
        provider_info['platform'] = platform

    if not provider_info.get('type'):
        # 3.  Collect provider type
        print "Select a provider type for your new provider"
        print "1: Openstack"
        while True:
            provider_type = raw_input("Select a provider type [1]: ")
            #NOTE: this will be replaced with actual logic when necessary.
            if True:
                provider_type = openstack
                break
        provider_info['type'] = provider_type
    return provider_info


def get_admin_info(admin_info={}):
    if not admin_info.get('username'):
        print "What is the username of the provider admin?"
        admin_info['username'] = require_input("username of provider admin: ")

    if not admin_info.get('password'):
        print "What is the password of the provider admin?"
        admin_info['password'] = require_input("password of provider admin: ")

    if not admin_info.get('tenant'):
        print "What is the tenant_name of the provider admin?"
        admin_info['tenant'] = require_input("tenant_name of provider admin: ")
    return admin_info


def get_provider_credentials(credential_info={}):
    admin_url = None
    auth_url = None

    if not credential_info.get('admin_url'):
        print "What is the admin_url for the provider?"
        admin_url = require_input("admin_url for the provider: ", get_valid_url)
        credential_info['admin_url'] = admin_url

    if not credential_info.get('auth_url'):
        print "What is the auth_url for the provider?"
        auth_url = require_input("auth_url for the provider: ", get_valid_url)
        credential_info['auth_url'] = auth_url

    if not credential_info.get('router_name'):
        print "What is the router_name for the provider?"
        credential_info['router_name'] = require_input("router_name for the provider: ")

    if not credential_info.get('region_name'):
        print "What is the region_name for the provider?"
        credential_info['region_name'] = require_input("region_name for the provider: ")

    if not credential_info.get('ex_force_auth_version'):
        print "What is the Authentication Scheme (Openstack ONLY -- Default:'2.0_password')?"
        ex_force_auth_version = require_input("ex_force_auth_version for the provider: ", lambda answer: answer in ['2.0_password','3.x_password'])
        credential_info['ex_force_auth_version'] = ex_force_auth_version

    return credential_info


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


    parser.add_argument("--from-openrc", dest="openrc",
                        help="Add a new provider from an openrc file.")
    parser.add_argument("--from-json", dest="json",
                        help="Add a new provider from a json file.")

    arguments = parser.parse_args()

    provider_info = admin_info = provider_credentials = {}
    if arguments.json:
        (provider_info,
         admin_info,
         provider_credentials) = read_json_file(arguments.json)
    elif arguments.openrc:
        (provider_info,
         admin_info,
         provider_credentials) = read_openrc_file(arguments.openrc)
    
    while True:
        get_provider_info(provider_info)
        get_admin_info(admin_info)
        get_provider_credentials(provider_credentials)
        review_information(provider_info, admin_info, provider_credentials)
        if provider_info and admin_info and provider_credentials:
            break

    new_provider = create_provider(provider_info)
    create_provider_credentials(new_provider, provider_credentials)
    create_admin(new_provider, admin_info)
    print "You still need to create an AllocationStrategy. Go into the admin panel and select a Strategy *BEFORE* you use Atmosphere"

if __name__ == "__main__":
    main()
