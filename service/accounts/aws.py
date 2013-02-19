from atmosphere import settings
from atmosphere.logger import logger
from core.models.euca_key import Euca_Key
from core.models.identity import Identity
from core.models.group import Group, IdentityMembership, ProviderMembership
from core.models.provider import Provider 
from core.models.credential import Credential
from core.models.quota import Quota
from service.drivers.openstackUserManager import UserManager

class AccountDriver():
    aws_prov = None

    def __init__(self, *args, **kwargs):
        self.aws_prov = Provider.objects.get(location='EC2_US_EAST')

    def create_usergroup(self, username):
        user = User.objects.get_or_create(username=username)[0]
        group = Group.objects.get_or_create(name=username)[0]

        user.groups.add(group)
        user.save()
        group.leaders.add(user)
        group.save()
        return (user, group)

    def create_aws_identity(self, username, key, secret):
        """
        Create a new AWS identity (key/secret required) for User:<username>
        """
        (user, group) = self.create_usergroup(username)
        
        try:
            prov_member  = ProviderMembership.objects.get(provider=self.aws_prov, member__name=username)
            id_member = IdentityMembership.objects.filter(
                                                    identity__provider=self.aws_prov, 
                                                    member__name=username, 
                                                    identity__credential__value__in=[key, secret]).distinct()[0]
            return id_member.identity
        except (IndexError, ProviderMembership.DoesNotExist) as dne:
            #Add provider membership
            prov_member = ProviderMembership.objects.get_or_create(provider=self.aws_prov, member=group)[0]
            #Remove the user line when quota model is fixed
            default_quota = Quota().defaults()
            quota = Quota.objects.filter(cpu=default_quota['cpu'], memory=default_quota['memory'], storage=default_quota['storage'])[0]
            #Create the Identity
            identity = Identity.objects.get_or_create(created_by=user, provider=self.aws_prov)[0] #Build & Save
            key_cred = Credential.objects.get_or_create(identity=identity, key='key', value=key)[0]
            sec_cred = Credential.objects.get_or_create(identity=identity, key='secret', value=secret)[0]
            #Link it to the usergroup
            id_member = IdentityMembership.objects.get_or_create(identity=identity, member=group, quota=quota)[0]
            #Return the identity
            return id_member.identity
