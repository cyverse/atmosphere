"""
UserManager:
  Remote Eucalyptus Admin controls..

User, BooleanField, StringList
  These XML parsing classes belong to euca_admin.py, and can be found on the Cloud Controller
TODO: Remove keys and add this to github, people using openstack will appreciate it.
"""
from hashlib import sha1

from django.contrib.auth.models import User

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
    user_manager = None
    openstack_prov = None

    def __init__(self, *args, **kwargs):
        self.user_manager = UserManager.settings_init()
        self.openstack_prov  = Provider.objects.get(location='OPENSTACK')

    def create_user(self, username, usergroup=True, admin=False):

        password = self.hashpass(username)
        if usergroup:
            (tenant, user, role) = self.user_manager.addUsergroup(username,password,True,admin)
        else:
            user = self.user_manager.addUser(username, password)
        return (user.name, password)

    def delete_user(self, username, usergroup=True, admin=False) :
        if usergroup:
            deleted = self.user_manager.deleteUsergroup(username)
        else:
            deleted = self.user_manager.deleteUser(username)
        return deleted

    def create_key(self, user_dict):
        try:
            return Euca_Key.objects.get(username=user_dict['username'])
        except Euca_Key.DoesNotExist, dne:
            return Euca_Key.objects.create(\
                    username=user_dict['username'],\
                    ec2_access_key=user_dict['access_key'],\
                    ec2_secret_key=user_dict['secret_key'],\
                    ec2_url=settings.EUCA_EC2_URL,\
                    s3_url=''\
                    )
        except Euca_Key.MultipleObjectsReturned, mor:
            #Delete all objects matching this user
            Euca_Key.objects.filter(username=user_dict['username']).delete()
            return Euca_Key.objects.create(\
                    username=user_dict['username'],\
                    ec2_access_key=user_dict['access_key'],\
                    ec2_secret_key=user_dict['secret_key'],\
                    ec2_url=settings.EUCA_EC2_URL,\
                    s3_url=''\
                    )

    def create_usergroup(self, username):
        user = User.objects.get_or_create(username=username)[0]
        group = Group.objects.get_or_create(name=username)[0]

        user.groups.add(group)
        user.save()
        group.leaders.add(user)
        group.save()
        return (user, group)

    def create_openstack_identity(self, username, password, tenant_name):
        (user, group) = self.create_usergroup(username)
        
        try:
            prov_member  = ProviderMembership.objects.get(provider=self.openstack_prov, member__name=username)
            id_member = IdentityMembership.objects.filter(
                                                    identity__provider=self.openstack_prov, 
                                                    member__name=username, 
                                                    identity__credential__value__in=[username,password, tenant_name]).distinct()[0]
            tenant_cred = Credential.objects.get_or_create(identity=id_member.identity, key='ex_tenant_name', value=tenant_name)[0]
            return id_member.identity
        except (IndexError, ProviderMembership.DoesNotExist) as dne:
            #Add provider membership
            prov_member = ProviderMembership.objects.get_or_create(provider=self.openstack_prov, member=group)[0]
            #Remove the user line when quota model is fixed
            default_quota = Quota().defaults()
            quota = Quota.objects.filter(cpu=default_quota['cpu'], memory=default_quota['memory'], storage=default_quota['storage'])[0]
            #Create the Identity
            identity = Identity.objects.get_or_create(created_by=user, provider=self.openstack_prov)[0] #Build & Save
            key_cred = Credential.objects.get_or_create(identity=identity, key='key', value=username)[0]
            sec_cred = Credential.objects.get_or_create(identity=identity, key='secret', value=password)[0]
            tenant_cred = Credential.objects.get_or_create(identity=identity, key='ex_tenant_name', value=tenant_name)[0]
            #Link it to the usergroup
            id_member = IdentityMembership.objects.get_or_create(identity=identity, member=group, quota=quota)[0]
            #Return the identity
            return id_member.identity

    def hashpass(self, username):
        return sha1(username).hexdigest()

    def get_user(self, user):
        return self.user_manager.getUser(user)

    def list_users(self):
        return self.user_manager.listUsers()
