#!/usr/bin/env python
"""
Create access token for users

Usage:
    python scripts/batch_create_access_token.py --token-name workshop_token --users name1,name2,name3
"""
import django

django.setup()

from core.models import AccessToken
from core.models.user import AtmosphereUser
from core.models.access_token import create_access_token

import argparse
import csv
import json


def parse_arg():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: result
    """
    parser = argparse.ArgumentParser(
        description="create or fetch tokens for users"
    )
    parser.add_argument(
        "--users",
        dest="users",
        type=str,
        required=True,
        help="usernames, comma separated if more than 1(no space)"
    )
    parser.add_argument(
        "--token-name",
        dest="token_name",
        type=str,
        required=True,
        help="name of the token"
    )

    args = parser.parse_args()
    args.users = args.users.split(',')
    return args


def fetch_user_by_username(username):
    """
    Fetch user by username

    Args:
        username (str): username of the user

    Returns:
        Optional[AtmosphereUser]: user
    """
    try:
        return AtmosphereUser.objects.get(username=username)
    except Exception as exc:
        print("unable to fetch user {}".format(username))
        print(exc)
        return None


def create_or_fetch_token_for_user(user, token_name):
    """
    Fetch token with given name for user, create a token if none exists with the same name

    Args:
        user (AtmosphereUser): user
        token_name (str): name of the token

    Returns:
        str: token
    """
    # check if there is any existing token by the same name
    existing_tokens = AccessToken.objects.filter(token__user=user)
    for token in existing_tokens:
        if token.name == token_name:
            # return token if same name
            return token.token_id
    # create new token if none with the same name exists
    new_token = create_access_token(
        user, token_name, issuer="Personal-Access-Token"
    )
    print("new token created for user {}".format(user.username))
    return new_token.token_id


def main():
    """
    Entrypoint
    """
    args = parse_arg()
    for username in args.users:
        user = fetch_user_by_username(username)
        token = create_or_fetch_token_for_user(user, args.token_name)
        print("{}, {}".format(username, token))


if __name__ == '__main__':
    main()
