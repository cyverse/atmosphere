"""
UserManager:
  Remote Eucalyptus Admin controls..

User, BooleanField, StringList
  These XML parsing classes belong to euca_admin.py,
  and can be found on the Cloud Controller
"""
from core.models import AtmosphereUser as User
from django.db.models import Max

from threepio import logger

from core.models.identity import Identity
from core.models.provider import Provider

from rtwo.drivers.eucalyptus_user import UserManager
from chromogenic.drivers.eucalyptus import ImageManager

from atmosphere import settings


class AccountDriver():
    user_manager = None
    image_manager = None
    core_provider = None

    def __init__(self, provider):
        if not provider:
            provider = Provider.objects.get(location='EUCALYPTUS')
        self.core_provider = provider

        # credential dicts
        admin_creds = provider.get_admin_identity().get_credentials()
        provider_creds = provider.get_credentials()
        self.provider_creds = provider_creds
        # Merge credential dicts
        all_creds = provider_creds
        all_creds.update(admin_creds)
        # Convert creds for each manager
        self.user_creds = self._build_user_creds(all_creds)
        self.user_manager = UserManager(**self.user_creds)

        self.image_creds = self._build_image_creds(all_creds)
        self.image_manager = ImageManager(**self.image_creds)

    def _build_image_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build a "UserManager" object
        """
        img_args = credentials.copy()
        # Required args:
        img_args.get('key')
        img_args.get('secret')

        img_args.get('config_path')
        img_args.get('ec2_cert_path')
        img_args.get('ec2_url')
        img_args.get('euca_cert_path')
        img_args.get('pk_path')
        img_args.get('s3_url')
        # Root dir to find extras/...
        img_args.get('extras_root', settings.PROJECT_ROOT)
        # Remove if exists:
        img_args.pop('account_path')
        return img_args

    def _build_user_creds(self, credentials):
        """
        Credentials - dict()

        return the credentials required to build a "UserManager" object
        """
        user_args = credentials.copy()
        # Required args:
        user_args.get('key')
        user_args.get('secret')
        user_args.get('account_path')
        # ec2_url//url required for user_manager
        if not user_args.get('url', None):
            user_args['url'] = user_args.pop('ec2_url', None)
        # Remove if exists:
        user_args.pop('config_path', None)
        user_args.pop('ec2_cert_path', None)
        user_args.pop('euca_cert_path', None)
        user_args.pop('pk_path', None)
        user_args.pop('s3_url', None)
        return user_args

    def create_account(self, euca_user, max_quota=False, account_admin=False):
        """
        TODO: Logic to create the account via euca call should go here,
        create_identity should be called after account is established
        """

        if isinstance(euca_user, str):
            euca_user = self.get_user(euca_user)

        identity = self.create_identity(
            euca_user['username'],
            euca_user['access_key'], euca_user['secret_key'],
            max_quota=max_quota, account_admin=account_admin)
        return identity

    def create_identity(self, euca_user, max_quota=False, account_admin=False):
        """
        euca_user - A dictionary containing 'access_key',
                    'secret_key', and 'username'
        max_quota - Set this user to have the maximum quota,
                    instead of the default quota
        """
        if isinstance(euca_user, str):
            euca_user = self.get_user(euca_user)
        return self.create_identity(euca_user['username'],
                                    euca_user['access_key'],
                                    euca_user['secret_key'],
                                    max_quota=max_quota,
                                    account_admin=account_admin)

    def create_identity(self, username, access_key, secret_key,
                        max_quota=False, account_admin=False):
        """
        """
        identity = Identity.create_identity(
            username, self.core_provider.location,
            max_quota=max_quota, account_admin=account_admin,
            cred_key=access_key, cred_secret=secret_key)

        return identity

    def clean_credentials(self, credential_dict):
        creds = ["username", "access_key", "secret_key"]
        missing_creds = []
        # 1. Remove non-credential information from the dict
        for key in credential_dict.keys():
            if key not in creds:
                credential_dict.pop(key)
        # 2. Check the dict has all the required credentials
        for c in creds:
            if not hasattr(credential_dict, c):
                missing_creds.append(c)
        return missing_creds

    def add_user(self, username):
        userCreated = self.user_manager.add_user(username)
        if not userCreated:
            return None
        user = self.user_manager.get_user(username)
        return user

    def delete_identity(self, username):
        ident = Identity.objects.get(
            created_by__username=username, provider=core_provider)
        return ident.delete()

    def delete_user(self, username):
        userDeleted = self.user_manager.delete_user(username)
        return userDeleted

    def get_key(self, user):
        return self.user_manager.get_key(user)

    def get_keys(self, userList):
        return self.user_manager.get_keys(userList)

    def get_user(self, user):
        return self.user_manager.get_user(user)

    def get_users(self, userList):
        return self.user_manager.get_users(userList)

    def list_all_images(self):
        return self.image_manager.list_images()

    def list_users(self):
        return self.user_manager.get_all_users()
