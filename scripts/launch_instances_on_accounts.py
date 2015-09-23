#!/usr/bin/env python
import argparse
import json
import sys

import requests
import gevent

from atmosphere import settings
from core.models import AtmosphereUser as User, Provider, Identity
from iplantauth.models import Token

from gevent import monkey

# patches stdlib (including socket and ssl modules) to cooperate with
# other greenlets
monkey.patch_socket()
monkey.patch_ssl()

import django
if django.VERSION >= (1, 7):
    django.setup()


def launch_instance(launch_url, headers, data, provider, user):
    print "Sending request"
    r = requests.post(launch_url, headers=headers, data=data)
    if r.status_code == 201:
        print "Instance launched successfully: %s, %s" % (provider.location, user.username)
    else:
        print "Instance failed to launch: %s, %s, %s" % (provider.location, user.username, r.status_code)
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
        launch_url = ("%s/api/v1/provider/%s/identity/%s/instance"
                      % (settings.SERVER_URL, provider.uuid, identity.uuid))

        user_tokens = Token.objects.filter(user=user).order_by('-issuedTime')
        if user_tokens.count() == 0:
            print(
                "No tokens for user: " +
                user.username +
                ". No instances will launch on their account.")
            continue

        latest_token = user_tokens[0]

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Token ' + latest_token.key
        }

        payload = {
            'machine_alias': args.image,
            'name': args.name,
            'size_alias': args.size
        }

        for x in range(args.count):
            job = gevent.spawn(
                launch_instance,
                launch_url,
                headers,
                json.dumps(payload),
                provider,
                user)
            async_request_list.append(job)

    print "Sending requests to Atmosphere..."
    gevent.joinall(async_request_list)
    print "Script finished running successfully!"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Launch images to a cloud for testing")

    parser.add_argument(
        "image",
        type=str,
        default="2436bf2f-13a7-4118-a349-d3529f79ae16",
        help="The id of the image to be launched")

    parser.add_argument(
        "--users",
        required=True,
        help="List of users for whom images will be launched")

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

    parser.add_argument(
        "--count",
        type=int,
        default=4,
        help="The number of images to be launched for each user")

    parser.add_argument(
        "--size",
        type=str,
        default="1",
        help="The size of the machine used to deploy the image")

    args = parser.parse_args()
    main(args)
