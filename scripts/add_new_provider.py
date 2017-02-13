#!/usr/bin/env python

# DEPRECATION WARNING -- Will be removed in favor of contacting the Atmosphere API directly
# or using the GUI to instantiate provider + accounts
import argparse
import json
import pprint
import sys
import subprocess

import django; django.setup()
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
import libcloud.security

from urlparse import urlparse, urljoin

from core.models import Provider, PlatformType, ProviderType, Identity, Group,\
    IdentityMembership, AccountProvider, Quota, ProviderInstanceAction
from core.models import InstanceAction
from service.driver import get_account_driver
from service.networking import topology_list
from atmosphere.settings import secrets
from atmosphere import settings

libcloud.security.VERIFY_SSL_CERT = False
libcloud.security.VERIFY_SSL_CERT_STRICT = False
KVM = PlatformType.objects.get_or_create(name='KVM')[0]
XEN = PlatformType.objects.get_or_create(name='Xen')[0]
openstack = ProviderType.objects.get_or_create(name='OpenStack')[0]

url_validator = URLValidator()


def require_input(
        question, validate_answer=None,
        default=None, blank=False, allow_falsy=False, use_validated_answer=False):
    try:
        while True:
            answer = raw_input(question)
            if not answer and default:
                answer = default
            if not answer and not blank:
                print "ERROR: Cannot leave this answer blank!"
                continue
            if validate_answer:
                validated_answer = validate_answer(answer)
                if not validated_answer and not allow_falsy:
                    continue
                elif use_validated_answer:
                    answer = validated_answer
            break
        return answer
    except (KeyboardInterrupt, EOFError):
        print "ERROR: Script has been cancelled."
        sys.exit(1)


def review_information(provider_info, admin_info, provider_credentials, cloud_config):
    """
    """
    print "1. Provider Information"
    pprint.pprint(provider_info)
    print "1. Provider Cloud config"
    pprint.pprint(cloud_config)
    print "2. Admin Information"
    pprint.pprint(admin_info)
    print "3. Provider Credentials"
    pprint.pprint(provider_credentials)
    #jsonfile_text = json.dumps({'provider':provider_info, 'admin': admin_info, 'credentials': provider_credentials})
    #print jsonfile_text
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


def yes_no_truth(raw_text):
    if raw_text.lower().strip() == 'yes':
        return True
    else:
        return False

def get_comma_list(raw_text):
    """
    Return a list from comma separated string.
    (Protect against ', ' by stripping white-space from entries.)
    """
    try:
        [entry.strip() for entry in raw_text.split(',')]
    except Exception:
        raise ValidationError("Invalid text: %s" % raw_text)
    return raw_text


def get_valid_url(raw_url):
    try:
        url_validator(raw_url)
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
        raise
        print("Invalid file format expected a json file.")
        raise

    provider_info = info["provider"]
    admin_info = info["admin"]
    credential_info = info["credential"]
    cloud_config = info["cloud_config"]

    return provider_info, admin_info, credential_info, cloud_config


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
        "public_routers": None,
        "region_name": os_environ["OS_REGION_NAME"]
    }
    return provider_info, admin_info, credential_info


def get_provider_info(provider_info={}):
    # 1.  Collect name
    platform = None
    if not provider_info.get('name'):
        print "What is the name of your new provider?"
        provider_info['name'] = require_input("Name of new provider: ")
    if not provider_info.get('public'):
        print "Would you like Atmosphere to make this provider public?"
        print "Images on Public providers are advertised on Troposphere UI without authentication."
        print "Generally, users will have an identity created on each public provider."
        provider_info['public'] = require_input(
        "Is this provider public? (yes/[no]): ",
        yes_no_truth, default='no', allow_falsy=True, use_validated_answer=True)
    # 2.  Collect platform type
    if not provider_info.get('platform'):
        print "Select a platform type for your new provider"
        print "1: KVM (Default), 2: Xen"
        platform = require_input("Select a platform type ([1]/2): ", lambda answer: answer in ['1','2'], default='1')
        if platform == '1':
            platform = KVM
        elif platform_choice == '2':
            platform = XEN
        provider_info['platform'] = platform

    if not provider_info.get('type'):
        # 3.  Collect provider type
        # NOTE: this will be replaced with actual logic when necessary.
        # print "Select a provider type for your new provider"
        # print "1: Openstack"
        # provider_type = require_input("Select a provider type [1]", default=openstack)
        provider_type = openstack
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


def get_cloud_config(cloud_config={}):
    if cloud_config:
        net_config = cloud_config.get('network', {})
        user_config = cloud_config.get('user', {})
        deploy_config = cloud_config.get('deploy', {})
    else:
        net_config = {}
        user_config = {}
        deploy_config = {}

    set_user_config(user_config)
    set_deploy_config(deploy_config)
    set_network_config(net_config)
    return {
        'user': user_config,
        'deploy': deploy_config,
        'network': net_config,
    }


def set_deploy_config(deploy_config):
    #get/set deploy_format
    hostname_format = deploy_config.get('hostname_format')
    if not hostname_format:
        print "What is the hostname format for the instances deployed by your provider? (Default selection will use IP address as hostname)"
        hostname_format = require_input("hostname_format for the provider (Default: <Use IP Address>): ", default='%(one)s.%(two)s.%(three)s.%(four)s')
    deploy_config.update({'hostname_format': hostname_format})
    return deploy_config


def set_network_config(net_config):
    #FIXME/TODO: This is probably not an effective way of collecting data..
    if not net_config.get('default_security_rules'):
        print "What is the list of security rules for the provider? (Default: Uses the setting `DEFAULT_RULES`)"
        net_config['default_security_rules'] = require_input("default_security_rules for provider: (Should be a list)", default=settings.DEFAULT_RULES)

    if not net_config.get('dns_nameservers'):
        print "What is the list of DNS Nameservers for the provider? (Default: Uses google DNS servers [8.8.8.8, 8.8.4.4])"
        net_config['dns_nameservers'] = require_input("dns_nameservers for provider: (Should be a list)", default=settings.DEFAULT_NAMESERVERS)

    if not net_config.get('topology'):
        print "Which Network Topology should be used for your provider? (Default: External Router)"
        choices = topology_list()
        for idx, choice in enumerate(choices):
            print "%s:" % idx,
            pprint.pprint(choice)
        topology = require_input("Select the topology name by number: ", lambda answer: choices[int(answer)] if int(answer) < len(choices) else None, default='0')
        topology_name = topology.name
    else:
        topology_name = net_config['topology']

    net_config['topology'] = topology_name
    return net_config


def set_user_config(user_config):
    #get/set admin_role_name
    admin_role_name = user_config.get('admin_role_name')
    if not admin_role_name:
        print "What is the role name for 'admin' in your provider? (Default: admin)"
        admin_role_name = require_input("admin role_name for the provider: ", default='admin')

    #get/set user_role_name
    user_role_name = user_config.get('user_role_name')
    if not user_role_name:
        print "What is the role name for default membership in your provider? (Default: _member_)"
        user_role_name = require_input("user_role_name for the provider: ", default='_member_')

    #get/set domain
    domain = user_config.get('domain')
    if not domain:
        print "What is the domain name for your provider? (Default: default)"
        domain = require_input("domain name for the provider: ", default='default')

    secret = user_config.get('secret')
    if not secret or len(secret) < 32:
        secret = require_input("What secret would you like to use to create " +
                "user accounts? (32 character minimum) ",
                lambda answer: len(answer) >= 32)
    user_config.update({
        'admin_role_name': admin_role_name,
        'user_role_name': user_role_name,
        'domain': domain,
        'secret': secret,
    })
    return user_config


def get_provider_credentials(credential_info={}):
    admin_url = None
    auth_url = None

    if not credential_info.get('admin_url'):
        print "What is the admin_url for the provider? (scheme://host:port)"
        admin_url = require_input("admin_url for the provider: ", get_valid_url)
        credential_info['admin_url'] = admin_url

    if not credential_info.get('auth_url'):
        print "What is the auth_url for the provider? (scheme://host:port)"
        auth_url = require_input("auth_url for the provider: ", get_valid_url)
        credential_info['auth_url'] = auth_url

    if not credential_info.get('public_routers'):
        print "List the public routers available for the provider, comma-separated. (Ex: public-router,atmosphere-router -- NOTE: If you are using one-user-per-router, this value will be ignored))"
        credential_info['public_routers'] = require_input("List of public routers (comma-separated): ", get_comma_list, blank=True)

    if 'network_name' not in credential_info:
        print "The external/public network that will Atmosphere instances will connect to in order to communicate. (NOTE: If you are *NOT* using one-user-per-router (One-user-per-network), this value will be ignored.)"
        credential_info['network_name'] = require_input("External network name: ", blank=True)

    if not credential_info.get('region_name'):
        print "What is the region_name for the provider?"
        credential_info['region_name'] = require_input("region_name for the provider: ")

    if not credential_info.get('ex_force_auth_version'):
        print "What is the Authentication Scheme (Openstack ONLY -- Default:'2.0_password')?"
        ex_force_auth_version = require_input("ex_force_auth_version for the provider: ", lambda answer: answer in ['2.0_password','3.x_password'], default='2.0_password')
        credential_info['ex_force_auth_version'] = ex_force_auth_version
    # Verify that 'admin_url' is properly set.
    auth_version = credential_info['ex_force_auth_version']

    admin_url = credential_info['admin_url']
    if '2' in auth_version and '/v2.0/tokens' not in admin_url:
        print "Note: Adding '/v2.0/tokens' to the end of the admin_url path (Required for 2.0_password)"
        credential_info['admin_url'] = urljoin(admin_url, '/v2.0/tokens')

    auth_url = credential_info['auth_url']
    if '2' in auth_version and '/v2.0/tokens' not in auth_url:
        print "Note: Adding '/v2.0/tokens' to the end of the auth_url path (Required for 2.0_password)"
        credential_info['auth_url'] = urljoin(auth_url, '/v2.0/tokens')


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

    try:
        new_identity = Identity.objects.get(provider=provider,
                                            created_by=user)
    except Identity.DoesNotExist:
        new_identity = Identity.objects.create(
            provider=provider,
            created_by=user,
            quota=Quota.default_quota())
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
        identity=new_identity, member=group)

    return new_identity


def create_provider(provider_info, provider_credentials={}, cloud_config={}):
    REQUIRED_FIELDS = ["name", "platform", "public", "type"]

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
        type=provider_info["type"],
        cloud_config=cloud_config,
        public=provider_info["public"])
    # 3b. Associate all InstanceActions
    instance_actions = InstanceAction.objects.all()
    for action in instance_actions:
        ProviderInstanceAction.objects.get_or_create(
            provider=new_provider,
            instance_action=action,
            enabled=True)
    # 4.  Create a new provider
    print "Created a new provider: %s" % (new_provider.location)
    # 5. Add the provider specific credentials
    create_provider_credentials(new_provider, provider_credentials)
    return new_provider


def create_provider_credentials(provider, credential_info):
    REQUIRED_FIELDS = ["admin_url", "auth_url", "public_routers", "region_name"]

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

    provider_info = {}
    admin_info = {}
    provider_credentials = {}
    cloud_config = {}
    if arguments.json:
        (provider_info,
         admin_info,
         provider_credentials,
         cloud_config) = read_json_file(arguments.json)
    elif arguments.openrc:
        (provider_info,
         admin_info,
         provider_credentials) = read_openrc_file(arguments.openrc)
    
    while True:
        get_provider_info(provider_info)
        get_admin_info(admin_info)
        get_provider_credentials(provider_credentials)
        get_cloud_config(cloud_config)
        review_information(provider_info, admin_info, provider_credentials, cloud_config)
        if not provider_info or not admin_info or not provider_credentials or not cloud_config:
            continue
        new_provider = create_provider(provider_info, provider_credentials, cloud_config)
        new_identity = create_admin(new_provider, admin_info)
        is_valid = validate_new_provider(new_provider, new_identity)
        if is_valid:
            break
        else:
            new_identity.delete()
            new_provider.delete()
    # New provider created
    print "You still need to create an AllocationStrategy. Go into the admin panel and select a Strategy *BEFORE* you use Atmosphere"


def validate_new_provider(new_provider, new_identity):
    acct_driver = get_account_driver(new_provider)
    if not acct_driver:
        print "Could not create an account driver for the new Provider"\
                " %s - %s. Check your credentials and try again. "\
                "If you believe you are receiving this message in error, "\
                "AND you are able to use external CLI tools on this machine "\
                "to contact your cloud, please report the issue to a developer!"\
                % (new_provider, new_identity)
        return False
    return True


if __name__ == "__main__":
    main()
