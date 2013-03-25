import os

from keystoneclient.exceptions import NotFound, ClientException
from keystoneclient.v2_0 import client as ks_client
from novaclient.v1_1 import client as nova_client

from atmosphere.logger import logger
from atmosphere import settings

import os
"""
OpenStack CloudAdmin Libarary
    Use this library to:
    * manage users within Keystone - openstack auth 
    
"""

class UserManager():
    keystone = None
    nova = None
    user = None
    password  = None
    tenant  = None

    @classmethod
    def settings_init(self, *args, **kwargs):
        settings_args = {
            'username': settings.OPENSTACK_ADMIN_KEY, 
            'password': settings.OPENSTACK_ADMIN_SECRET, 
            'tenant_name': settings.OPENSTACK_ADMIN_TENANT,
            'auth_url': settings.OPENSTACK_ADMIN_URL,
            'region_name': settings.OPENSTACK_DEFAULT_REGION
        }
        settings_args.update(kwargs)
        manager = UserManager(*args, **settings_args)
        return manager

    @classmethod
    def lc_driver_init(self, lc_driver, region=None, *args, **kwargs):
        lc_driver_args = {
        'username':lc_driver.key,
		'password':lc_driver.secret,
		'tenant_name':lc_driver._ex_tenant_name,
		'auth_url':lc_driver._ex_force_auth_url,
		'region_name':region if region else settings.OPENSTACK_DEFAULT_REGION
        }
        lc_driver_args.update(kwargs)
        manager = UserManager(*args, **lc_driver_args)
        return manager

    def __init__(self, *args, **kwargs):
        self.newConnection(*args, **kwargs)#username,password,tenant_name,auth_url)

    def newConnection(self,*args, **kwargs):
        self.keystone = ks_client.Client(*args, **kwargs)
        logger.warn(kwargs)
        self.nova = nova_client.Client(kwargs.pop('username'),
                                       kwargs.pop('password'),
                                       kwargs.pop('tenant_name'),
                                       kwargs.pop('auth_url'),
                                       kwargs.pop('region_name'), 
                                       *args, no_cache=True, **kwargs)
        self.nova.client.region_name = settings.OPENSTACK_DEFAULT_REGION
        #username=username,password=password,auth_url=auth_url, tenant_name=tenantname)

    ##Composite Classes##
    def addUsergroup(self, username, password, createUser=True, adminRole=False):
        """
        Create a group for this user only
        then create the user
        """
        #Create tenant for user/group
        tenant = self.addTenant(username)

        #Create user
        try:
            user= self.addUser(username, password, tenant.name)
        except ClientException as user_exists:
            user = self.getUser(username)

        logger.warn("Assign Tenant:%s Member:%s Role:%s" % (username, username, adminRole))
        try:
            role = self.addTenantMember(username, username, adminRole) # The user
        except ClientException as ce:
            logger.warn('Could not assign role to username %s' % username)
        try:
            role = self.addTenantMember(username, self.keystone.username, True)  # keystone admin always gets access, always has admin priv.
        except ClientException as ce:
            logger.warn('Could not assign admin role to username %s' % self.keystone.username)
        
        #TODO: Add teh default security group to this tenant using novaclient
        usergroup_nova  = nova_client.Client(self.keystone.username, self.keystone.password, tenant.name, self.nova.client.auth_url)
        usergroup_nova.client.region_name = settings.OPENSTACK_DEFAULT_REGION
        self.build_security_group(usergroup_nova)
        return (tenant, user, role)

    def build_security_group(self, nova, protocol_list = None):
        logger.warn("Gothere")
        if not protocol_list:
            #Build a "good" one.
            protocol_list = [
                ('TCP',22,22),
                ('TCP', 80,80),
                ('TCP',5900,5904),
                ('TCP',4200,4200),
                ('ICMP',-1,-1),
            ]
        #with nova.security_groups.find(name='default') as default_sec_group:
        default_sec_group = nova.security_groups.find(name='default')
        for (ip_protocol, from_port, to_port) in protocol_list:
            nova.security_group_rules.create(default_sec_group.id, ip_protocol=ip_protocol, from_port=from_port, to_port=to_port)
        logger.warn("Added all protocols")
        return nova.security_groups.find(name='default')

    def getUsergroup(self, username):
        return self.getTenant(username)

    def deleteUsergroup(self, username, deleteUser=True):
        try:
            self.deleteTenantMember(username, username, True)
        except ClientException as ce:
            logger.warn('Could not remove admin role from username %s' % username)
        try:
            self.deleteTenantMember(username, username, False)
        except ClientException as ce:
            logger.warn('Could not remove normal role from username %s' % username)
        try:
            self.deleteTenantMember(username, self.keystone.username, True)#Admin always gets access, always has admin priv.
        except ClientException as ce:
            logger.warn('Could not remove role from username %s' % self.keystone.username)

        if deleteUser:
            self.deleteUser(username)
        self.deleteTenant(username)

    ##ADD##
    def addRole(self, rolename):
        """
        Create a new role
        """
        return self.keystone.roles.create(name=rolename)
    def addTenant(self, groupname):
        """
        Create a new tenant
        """
        try:
            return self.keystone.tenants.create(groupname)
        except Exception, e:
            logger.warn(e)
            logger.warn(type(e))
            raise
    def addTenantMember(self, groupname, username, adminRole=False):
        """
        Adds user to group
        Invalid groupname, username, rolename : raise keystoneclient.exceptions.NotFound 
        """
        tenant = self.getTenant(groupname)
        user = self.getUser(username)
        #Only supporting two roles..
        if adminRole:
            role = self.getRole('adminRole')
        else:
            role = self.getRole('defaultMemberRole')
        try:
            return tenant.add_user(user,role)
        except Exception, e:
            logger.warn(type(e))
            logger.warn(e) 
            raise

    def addUser(self, username, password=None, groupname=None):
        """
        Create a new user
        Invalid groupname : raise keystoneclient.exceptions.NotFound 
        """
        kwargs = {
            'name':username,
            'password':password,
            'email':'%s@iplantcollaborative.org' % username,
        }
        if groupname:
            try:
                tenant = self.getTenant(groupname)
                kwargs['tenant_id'] = tenant.id
            except NotFound, nf:
                logger.warn("User does not exist")
                raise 
        return self.keystone.users.create(**kwargs)

    ##DELETE##
    def deleteRole(self, rolename):
        """
        Retrieve,Delete the user
        Invalid username : raise keystoneclient.exceptions.NotFound 
        """
        role = self.getRole(rolename)
        if role:
            role.delete()
        return True
    def deleteTenant(self, groupname):
        """
        Retrieve and delete the tenant/group matching groupname
        Returns True on success
        Invalid groupname : raise keystoneclient.exceptions.NotFound 
        """
        tenant = self.getTenant(groupname)
        if tenant:
            tenant.delete()
        return True

    def deleteTenantMember(self, groupname, username, adminRole=False):
        """
        Retrieves the tenant and user object 
        Removes user of the admin/member role
        Returns True on success
        Invalid username, groupname, rolename : raise keystoneclient.exceptions.NotFound 
        """
        tenant = self.getTenant(groupname)
        user = self.getUser(username)
        if adminRole:
            role = self.getRole('adminRole')
        else:
            role = self.getRole('defaultMemberRole')
        if not tenant or not user:
            return True
        try:
            tenant.remove_user(user,role)
            return True
        except NotFound, no_role_for_user:
            return True
        except Exception, e:
            logger.warn(type(e))
            logger.warn(e) 
            raise 

    def deleteUser(self, username):
        """
        Retrieve,Delete the user 
        Invalid username : raise keystoneclient.exceptions.NotFound 
        """
        user = self.getUser(username)
        if user:
            user.delete()
        return True

    def getRole(self, rolename):
        """
        Retrieve role 
        Invalid rolename : raise keystoneclient.exceptions.NotFound 
        """
        try:
            return self.keystone.roles.find(name=rolename)
        except NotFound, no_role:
            return None

    def getTenant(self, groupname):
        """
        Retrieve tenant
        Invalid groupname : raise keystoneclient.exceptions.NotFound 
        """
        try:
            return self.keystone.tenants.find(name=groupname)
        except NotFound, no_tenant:
            return None

    def getUser(self, username):
        """
        Retrieve user
        Invalid username : raise keystoneclient.exceptions.NotFound 
        """
        try:
            return self.keystone.users.find(name=username)
        except NotFound, no_user:
            return None


    def listRoles(self):
        return self.keystone.roles.list()

    def listTenants(self):
        return self.keystone.tenants.list()

    def listUsers(self):
        return self.keystone.users.list()

    

"""
Utility Functions
"""
def test():
    manager = UserManager.settings_init()

    (tenant, user, role) = manager.addUsergroup('estevetest03')
    print "Created test usergroup"

    print tenant, user, role

    manager.deleteUsergroup('estevetest03')
    print "Deleted test usergroup"

if __name__ == "__main__":
    test()
