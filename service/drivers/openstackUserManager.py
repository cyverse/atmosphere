import os

from keystoneclient.exceptions import NotFound, ClientException

from threepio import logger

from service.drivers.common import _connect_to_keystone,\
    _connect_to_nova, find
"""
OpenStack CloudAdmin Libarary
    Use this library to:
    * manage users within Keystone - openstack auth
"""


class UserManager():
    keystone = None
    nova = None
    user = None
    password = None
    project = None

    @classmethod
    def lc_driver_init(self, lc_driver, *args, **kwargs):
        lc_driver_args = {
            'username': lc_driver.key,
            'password': lc_driver.secret,
            'tenant_name': lc_driver._ex_tenant_name,
            'auth_url': lc_driver._ex_force_auth_url,
            'region_name': lc_driver._ex_force_service_region
        }
        lc_driver_args.update(kwargs)
        manager = UserManager(*args, **lc_driver_args)
        return manager

    def __init__(self, *args, **kwargs):
        self.newConnection(*args, **kwargs)

    def newConnection(self, *args, **kwargs):
        self.keystone = _connect_to_keystone(*args, **kwargs)
        self.nova = _connect_to_nova(*args, **kwargs)


    ##Composite Classes##
    def add_usergroup(self, username, password,
                     createUser=True, adminRole=False):
        """
        Create a group for this user only
        then create the user
        """
        #Create project for user/group
        project = self.add_project(username)

        #Create user
        try:
            user = self.add_user(username, password, project.name)
        except ClientException as user_exists:
            logger.debug('Received Error %s on add, User exists.' %
                         user_exists)
            user = self.get_user(username)

        logger.debug("Assign project:%s Member:%s Role:%s" %
                    (username, username, adminRole))
        try:
            role = self.add_project_member(username, username, adminRole)
        except ClientException:
            logger.warn('Could not assign role to username %s' % username)
        try:
            # keystone admin always gets access, always has admin priv.
            self.add_project_member(username, self.keystone.username, True)
        except ClientException:
            logger.warn('Could not assign admin role to username %s' %
                        self.keystone.username)
        return (project, user, role)

    def add_security_group_rule(self, nova, protocol, security_group):
        """
        Add a security group rule if it doesn't already exist.
        """
        (ip_protocol, from_port, to_port) = protocol
        if not self.find_rule(security_group, ip_protocol,
                          from_port, to_port):
            nova.security_group_rules.create(security_group.id,
                                             ip_protocol=ip_protocol,
                                             from_port=from_port,
                                             to_port=to_port)
        return True

    def build_security_group(self, username, password, project_name,
            protocol_list=None, *args, **kwargs):
        converted_kwargs = {
            'username':username,
            'password':password,
            'tenant_name':project_name,
            'auth_url':self.nova.client.auth_url,
            'region_name':self.nova.client.region_name}
        nova = _connect_to_nova(*args, **converted_kwargs)
        nova.client.region_name = self.nova.client.region_name
        if not protocol_list:
            #Build a "good" one.
            protocol_list = [
                ('TCP', 22, 22),
                ('TCP', 80, 80),
                ('TCP', 4200, 4200),
                ('TCP', 5500, 5500),
                ('TCP', 5666, 5666),
                ('TCP', 5900, 5904),
                ('TCP', 5900, 5999), # TEMP
                ('TCP', 9418, 9418),
                ('ICMP', -1, -1),
            ]
        default_sec_group = nova.security_groups.find(name='default')
        for protocol in protocol_list:
            self.add_security_group_rule(nova, protocol, default_sec_group)
        return nova.security_groups.find(name='default')

    def find_rule(self, security_group, ip_protocol, from_port, to_port):
        for r in security_group.rules:
            if r['from_port'] == from_port\
            and r['to_port'] == to_port\
            and r['ip_protocol'] == ip_protocol:
                return True
        return False

    def get_usergroup(self, username):
        return self.get_project(username)

    def delete_usergroup(self, username, deleteUser=True):
        try:
            self.delete_project_member(username, username, True)
        except ClientException:
            logger.warn('Could not remove admin role from username %s' %
                        username)
        try:
            self.delete_project_member(username, username, False)
        except ClientException:
            logger.warn('Could not remove normal role from username %s' %
                        username)
        try:
            self.delete_project_member(username, self.keystone.username, True)
        except ClientException:
            logger.warn('Could not remove role from keystone user %s' %
                        self.keystone.username)

        if deleteUser:
            self.delete_user(username)
        self.delete_project(username)

    ##ADD##
    def add_role(self, rolename):
        """
        Create a new role
        """
        return self.keystone.roles.create(name=rolename)

    def add_project(self, groupname):
        """
        Create a new project
        """
        try:
            return self.keystone_projects().create(groupname)
        except Exception, e:
            logger.exception(e)
            raise

    def add_project_member(self, groupname, username, adminRole=False):
        """
        Adds user to group
        Invalid groupname, username, rolename :
            raise keystoneclient.exceptions.NotFound
        """
        project = self.get_project(groupname)
        user = self.get_user(username)
        #Only supporting two roles..
        if adminRole:
            role = self.get_role('admin')
        else:
            role = self.get_role('defaultMemberRole')
        try:
            return project.add_user(user, role)
        except Exception, e:
            logger.exception(e)
            raise

    def add_user(self, username, password=None, groupname=None):
        """
        Create a new user
        Invalid groupname : raise keystoneclient.exceptions.NotFound
        """
        kwargs = {
            'name': username,
            'password': password,
            'email': '%s@iplantcollaborative.org' % username,
        }
        if groupname:
            try:
                project = self.get_project(groupname)
                kwargs['project_id'] = project.id
            except NotFound:
                logger.warn("User %s does not exist" % username)
                raise
        return self.keystone.users.create(**kwargs)

    ##DELETE##
    def delete_role(self, rolename):
        """
        Retrieve,Delete the user
        Invalid username : raise keystoneclient.exceptions.NotFound
        """
        role = self.get_role(rolename)
        if role:
            role.delete()
        return True

    def delete_project(self, groupname):
        """
        Retrieve and delete the project/group matching groupname
        Returns True on success
        Invalid groupname : raise keystoneclient.exceptions.NotFound
        """
        project = self.get_project(groupname)
        if project:
            project.delete()
        return True

    def delete_project_member(self, groupname, username, adminRole=False):
        """
        Retrieves the project and user object
        Removes user of the admin/member role
        Returns True on success
        Invalid username, groupname, rolename:
            raise keystoneclient.exceptions.NotFound
        """
        project = self.get_project(groupname)
        user = self.get_user(username)
        if adminRole:
            role = self.get_role('admin')
        else:
            role = self.get_role('defaultMemberRole')
        if not project or not user:
            return True
        try:
            project.remove_user(user, role)
            return True
        except NotFound as no_role_for_user:
            logger.debug('Error - %s: User-role combination does not exist' %
                         no_role_for_user)
            return True
        except Exception, e:
            logger.exception(e)
            raise

    def delete_user(self, username):
        """
        Retrieve,Delete the user
        Invalid username : raise keystoneclient.exceptions.NotFound
        """
        user = self.get_user(username)
        if user:
            user.delete()
        return True

    def get_role(self, rolename):
        """
        Retrieve role
        Invalid rolename : raise keystoneclient.exceptions.NotFound
        """
        try:
            return find(self.keystone.roles, name=rolename)
        except NotFound:
            return None

    def get_project(self, groupname):
        """
        Retrieve project
        Invalid groupname : raise keystoneclient.exceptions.NotFound
        """
        try:
            return find(self.keystone_projects(), name=groupname)
        except NotFound:
            return None

    def get_user(self, username):
        """
        Retrieve user
        Invalid username : raise keystoneclient.exceptions.NotFound
        """
        try:
            return find(self.keystone.users, name=username)
        except NotFound:
            return None

    def list_roles(self):
        return self.keystone.roles.list()

    def list_projects(self):
        return self.keystone_projects().list()

    def keystone_projects(self):
        if self.keystone.version == 'v3':
            return self.keystone.projects
        elif self.keystone.version == 'v2.0':
            return self.keystone.tenants

    def list_users(self):
        return self.keystone.users.list()

