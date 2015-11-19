#!/usr/bin/env python
import argparse
import sys

import requests
import gevent

from atmosphere import settings
from core.models import AtmosphereUser as User, Provider, Identity, Instance
from core.query import only_current
from iplantauth.models import Token

from gevent import monkey

# patches stdlib (including socket and ssl modules) to cooperate with
# other greenlets
monkey.patch_socket()
monkey.patch_ssl()

import django
if django.VERSION >= (1, 7):
    django.setup()


def delete_instance(launch_url, headers, provider, user):
    print "Sending request"
    print launch_url
    r = requests.delete(launch_url, headers=headers)
    if r.status_code in [200, 204]:
        print "Instance deleted successfully: %s, %s" % (provider.location, user.username)
    else:
        print "Instance failed to delete: %s, %s, %s" % (provider.location, user.username, r.status_code)
        print r.content


def main(args):
    users = User.objects.filter(username__in=args.users.split(","))
    try:
        provider = Provider.objects.get(id=args.provider_id)
    except Provider.DoesNotExist:
        print("A provider for id=%s could not be found" % args.provider_id)
        sys.exit(1)

    async_request_list = []

    for user in users:
        identity = Identity.objects.get(created_by=user, provider=provider)
        user_tokens = Token.objects.filter(user=user).order_by('-issuedTime')
        if user_tokens.count() == 0:
            print(
                "No tokens for user: " +
                user.username +
                ". No instances will launch on their account.")
            continue

        latest_token = user_tokens[0]

        headers = {
            'Authorization': 'Token ' + latest_token.key
        }

        instances = Instance.objects.filter(only_current(), created_by=user,
                                            name=args.name)

        for instance in instances:
            launch_url = settings.SERVER_URL + "/api/v1/provider/" + provider.uuid + \
                "/identity/" + identity.uuid + "/instance/" + instance.provider_alias
            job = gevent.spawn(
                delete_instance,
                launch_url,
                headers,
                provider,
                user)
            async_request_list.append(job)

    print "Sending requests to Atmosphere..."
    gevent.joinall(async_request_list)
    print "Script finished running successfully!"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Terminate images launched for testing")

    parser.add_argument(
        "--users",
        required=True,
        help="List of users for whom images will be terminated")

    parser.add_argument(
        "--provider-id",
        type=int,
        default=4,
        help="The id of the cloud provider to be used")

    parser.add_argument(
        "--name",
        type=str,
        default="Automated-Image-Launch",
        help="The name of the image to be launched")

    args = parser.parse_args()
    main(args)
