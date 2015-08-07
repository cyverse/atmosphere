from django.contrib.auth.models import User

from core.models.identity import Identity
from core.models.group import Group, IdentityMembership
from core.models.provider import Provider
from core.models.credential import Credential
from core.models.quota import Quota


class AccountDriver():
    aws_prov = None

    def __init__(self, *args, **kwargs):
        self.aws_prov = Provider.objects.get(location='EC2_US_EAST')

    def create_account(self, username, key, secret):
        """
        Create an identity with these credentials
        """
        identity = self.create_identity(username, key, secret)
        return identity

    def create_usergroup(self, username):
        user = User.objects.get_or_create(username=username)[0]
        group = Group.objects.get_or_create(name=username)[0]

        user.groups.add(group)
        user.save()
        group.leaders.add(user)
        group.save()
        return (user, group)

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

    def create_identity(self, username, key, secret):
        """
        Create a new AWS identity (key/secret required) for User:<username>
        """
        (user, group) = self.create_usergroup(username)

        try:
            id_member = IdentityMembership.objects.filter(
                identity__provider=self.aws_prov,
                member__name=username,
                identity__credential__value__in=[
                    access_key, secret_key]).distinct()[0]
            return id_member.identity
        except (IndexError, IdentityMembership.DoesNotExist):
            # Remove the user line when quota model is fixed
            default_quota = Quota().defaults()
            quota = Quota.objects.filter(cpu=default_quota['cpu'],
                                         memory=default_quota['memory'],
                                         storage=default_quota['storage'])[0]
            # Create the Identity
            identity = Identity.objects.get_or_create(
                created_by=user, provider=self.aws_prov)[0]
            Credential.objects.get_or_create(
                identity=identity, key='key', value=access_key)[0]
            Credential.objects.get_or_create(
                identity=identity, key='secret', value=secret_key)[0]
            # Link it to the usergroup
            id_member = IdentityMembership.objects.get_or_create(
                identity=identity, member=group, quota=quota)[0]
            # Return the identity
            return id_member.identity
