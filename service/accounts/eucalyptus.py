"""
UserManager:
  Remote Eucalyptus Admin controls..

User, BooleanField, StringList
  These XML parsing classes belong to euca_admin.py,
  and can be found on the Cloud Controller
"""
from django.contrib.auth.models import User
from django.db.models import Max

from threepio import logger

from core.models.identity import Identity
from core.models.provider import Provider

from rtwo.drivers.eucalyptus_user import UserManager

from atmosphere import settings

class AccountDriver():
    user_manager = None
    euca_prov = None

    def __init__(self):
        self.user_manager = UserManager(**settings.EUCALYPTUS_ARGS)
        self.euca_prov = Provider.objects.get(location='EUCALYPTUS')

    def create_account(self, euca_user, max_quota=False, account_admin=False):
        """
        TODO: Logic to create the account via euca call should go here,
        create_identity should be called after account is established
        """

        if type(euca_user) == str:
    	    euca_user = self.get_user(euca_user)

        identity = self.create_identity(
            euca_user['username'],
            euca_user['access_key'], euca_user['secret_key'],
            max_quota=max_quota, account_admin=account_admin)
        return identity

    def create_identity(self, euca_user, max_quota=False, account_admin=False):
        """
        euca_user - A dictionary containing 'access_key', 'secret_key', and 'username'
        max_quota - Set this user to have the maximum quota,
                    instead of the default quota
        """
        if type(euca_user) == str:
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
                username, self.euca_prov.location,
                max_quota=max_quota, account_admin=account_admin,
                cred_key=access_key, cred_secret=secret_key)

        return identity 


    def clean_credentials(self, credential_dict):
        creds = ["username", "access_key", "secret_key"]
        missing_creds = []
        #1. Remove non-credential information from the dict
        for key in credential_dict.keys():
            if key not in creds:
                credential_dict.pop(key)
        #2. Check the dict has all the required credentials
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

    def list_users(self):
        return self.user_manager.get_all_users()
