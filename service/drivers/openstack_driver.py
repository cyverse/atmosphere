"""
Extension of libcloud's OpenStack Node Driver.
"""
import binascii
import copy
import os
import socket
import sys
import time

import libcloud.compute.ssh
from libcloud.compute.ssh import SSHClient
from libcloud.compute.types import Provider, NodeState, DeploymentError,\
                                   LibcloudError
from libcloud.compute.base import StorageVolume,\
    NODE_ONLINE_WAIT_TIMEOUT, SSH_CONNECT_TIMEOUT,\
    NodeAuthPassword, NodeDriver
from libcloud.compute.drivers.openstack import OpenStack_1_1_NodeDriver
from libcloud.utils.py3 import httplib

from atmosphere.logger import logger

from service.drivers.openstackNetworkManager import NetworkManager


class OpenStack_Esh_NodeDriver(OpenStack_1_1_NodeDriver):
    """
    OpenStack node driver for esh.
    """

    features = {
        "_to_volume": ["Convert native object to StorageVolume"],
        "_to_size": ["Add cpu info to extra, duplicate of vcpu"],
        "_to_image": ["Add state info to extra"],
        "_to_node": ["Build public_ips field",
                     "public_ips as extra",
                     "keypairs as extra",
                     "user/tenant as extra"],
        "create_node": ["Create node with ssh_key", "ssh_key"],
        "ex_create_node_with_network": ["Create node with floating IP"
                                     " and ssh_key", "ssh_key"],
        "ex_deploy_to_node": ["Deploy to existing node"],
        "ex_suspend_node": ["Suspends the node"],
        "ex_resume_node": ["Resume the node"],
        "create_volume": ["Create volume"],
        "delete_volume": ["Delete volume"],
        "list_volumes": ["List all volumes"],
        "update_volume": ["Updates name and metadata on the volume"],
        "attach_volume": ["Attach volume to node"],
        "detach_volume": ["Detach volume from node"],
        "destroy_volume": ["Delete volume"],
        "ex_create_keypair": ["Adds a keypair given the public_key and name"],
        "ex_delete_keypair": ["Removes keypair matching name"],
        "ex_list_keypairs": ["List all keypairs for user"],
        "ex_list_floating_ip_pools": ["List all floating IP Pools"],
        "ex_allocate_floating_ip": ["Allocate floating IP"],
        "ex_deallocate_floating_ip": ["Deallocate floating IP"],
        "ex_associate_floating_ip": ["Associate floating IP with node"],
        "ex_disassociate_floating_ip": ["Disassociate floating IP from node"],
        "ex_list_volume_attachments": ["List all attached volumes for node"],
        "ex_get_volume_attachment": ["Get details about an attached volume"],
        "ex_create_security_group": ["Add security group to tenant"],
        "ex_delete_security_group": ["Delete security group from tenant"],
        "ex_list_security_groups": ["List all security groups for tenant"],
        "ex_add_security_group": ["Add security group to tenant"],
        "ex_remove_security_group": ["Remove security group from tenant"],
        "ex_create_security_group_rule": ["Add rule to a group"],
        "ex_delete_security_group_rule": ["Remove rule from a group"],
        "ex_list_security_group_rules": ["List all rules for a group"],
        "ex_get_limits": ["Get Rate and Absolute API limits"],
    }

    """
    Object builders -- Convert the native dict in to a Libcloud object
    """
    def _to_volumes(self, el):
        return [self._to_volume(volume) for volume in el['volumes']]

    def _to_volume(self, api_volume):
        extra = {
            'id': api_volume['id'],
            'displayName': api_volume['displayName'],
            'displayDescription': api_volume['displayDescription'],
            'size': api_volume['size'],
            'status': api_volume['status'],
            'metadata': api_volume['metadata'],
            'availabilityZone': api_volume['availabilityZone'],
            'snapshotId': api_volume['snapshotId'],
            'attachmentSet': api_volume['attachments'],
            'createTime': api_volume['createdAt'],
        }
        return StorageVolume(id=api_volume['id'],
                             name=api_volume['displayName'],
                             size=api_volume['size'],
                             driver=self,
                             extra=extra)

    def _to_size(self, api_size):
        """
        Extends Openstack_1_1_NodeDriver._to_size,
        adds support for cpu
        """
        size = super(OpenStack_Esh_NodeDriver, self)._to_size(api_size)
        size.extra = {'cpu': api_size['vcpus']}
        return size

    def _to_image(self, api_machine):
        """
        Extends Openstack_1_1_NodeDriver._to_image,
        adds support for architecture and state
        """
        image = super(OpenStack_Esh_NodeDriver, self)._to_image(api_machine)
        image.extra['state'] = api_machine['status'].lower()
        return image

    def _to_node(self, api_node):
        """
        Extends OpenStack_1_1_NodeDriver._to_node
        adding support for public and private ips.
        """
        def _set_ips():
            """
            Set up ips in the api_node so _to_node may call its super.
            """
            try:
                api_node['self'] = copy.deepcopy(api_node)
                #api_node['task'] = api_node['object']['OS-EXT-STS:task_state']
                api_node['addresses']['public'] = []
                api_node['addresses']['private'] = []

                #Retrieve all floating IPs that belong to this instance
                ips = [floating_ip for floating_ip
                       in self.ex_list_floating_ips()
                       if floating_ip['instance_id'] == api_node['id']]

                #Add all the IPs to the 'public_ips' list on the node
                for ip in ips:
                    ip_obj = {'version': 4, 'addr': ip['fixed_ip']}
                    if ip_obj not in api_node['addresses']['private']:
                        api_node['addresses']['private'].append(ip_obj)

                    ip_obj = {'version': 4, 'addr': ip['ip']}
                    if ip_obj not in api_node['addresses']['public']:
                        api_node['addresses']['public'].append(ip_obj)

                #If no floating IPs found, use the private IP given at startup
                if not ips:
                    for ip_group in api_node['addresses'].keys():
                        if api_node['addresses'][ip_group]\
                        and ip_group != 'private':
                            for address in api_node['addresses'][ip_group]:
                                api_node['addresses']['private'].append(
                                    address)
            except (IndexError, KeyError) as no_ip:
                logger.warn("No IP for node:%s" % api_node['id'])

        _set_ips()
        node = super(OpenStack_Esh_NodeDriver, self)._to_node(api_node)
        node.extra.update({
            'addresses': api_node['addresses'],
            'keypair': api_node['key_name'],
            'status': api_node['status'].lower(),
            'task': api_node['OS-EXT-STS:task_state'],
            'power': api_node['OS-EXT-STS:power_state'],
            'instancetype': api_node['flavor']['id'],
            'object': api_node
        })
        return node

    def create_node(self, **kwargs):
        self._add_keypair(kwargs)
        kwargs.update({
            'ex_keyname': unicode(self.key),
        })

        node = super(OpenStack_Esh_NodeDriver, self).create_node(**kwargs)

        #NOTE: This line is needed to authenticate via SSH_Keypair instead!
        node.extra['password'] = None

        return node

    def ex_create_node_with_network(self, **kwargs):
        """
        Deprecated -- Old Workflow (Via JMATT!)
        """
        self._add_keypair(kwargs)
        kwargs.update({
            'ex_keyname': unicode(self.key),
        })
        logger.debug("kwargs = %s" % kwargs)
        #Instance launches at this point.
        node = super(OpenStack_Esh_NodeDriver, self).create_node(**kwargs)

        #NOTE: This line is needed to authenticate via SSH_Keypair instead!
        node.extra['password'] = None

        #NOTE: Using this to wait for the time it takes to launch instance and have a valid IP port
        time.sleep(20)
        #TODO: It would be better to hook in an asnyc thread that waits for valid IP port
        #TODO: This belongs in a eelery task.
        server_id = node.id
        self._add_floating_ip(server_id, **kwargs)

        return node

    def ex_deploy_to_node(self, node, *args, **kwargs):
        """
        libcloud.compute.base.deploy_node
        """
        if not libcloud.compute.ssh.have_paramiko:
            raise RuntimeError('paramiko is not installed. You can install ' +
                               'it using pip: pip install paramiko')

        password = None

        if 'create_node' not in self.features:
            raise NotImplementedError(
                'deploy_node not implemented for this driver')
        elif 'generates_password' not in self.features["create_node"]:
            if 'password' not in self.features["create_node"] and \
               'ssh_key' not in self.features["create_node"]:
                raise NotImplementedError(
                    'deploy_node not implemented for this driver')

            if 'auth' not in kwargs:
                value = os.urandom(16)
                kwargs['auth'] = NodeAuthPassword(binascii.hexlify(value))

            if 'ssh_key' not in kwargs:
                logger.debug("ssh_key missing!")
                password = kwargs['auth'].password

        max_tries = kwargs.get('max_tries', 3)

        if 'generates_password' in self.features['create_node']:
            password = node.extra.get('password')

        ssh_interface = kwargs.get('ssh_interface', 'public_ips')

        # Wait until node is up and running and has IP assigned
        max_tries = kwargs.get('max_tries', 3)
        try:
            node, ip_addresses = self.wait_until_running(
                nodes=[node],
                wait_period=3, timeout=NODE_ONLINE_WAIT_TIMEOUT,
                ssh_interface=ssh_interface)[0]
        except Exception:
            e = sys.exc_info()[1]
            raise DeploymentError(node=node, original_exception=e, driver=self)

        if password:
            node.extra['password'] = password

        ssh_username = kwargs.get('ssh_username', 'root')
        ssh_alternate_usernames = kwargs.get('ssh_alternate_usernames', [])
        ssh_port = kwargs.get('ssh_port', 22)
        ssh_timeout = kwargs.get('ssh_timeout', 10)
        ssh_key_file = kwargs.get('ssh_key', None)
        timeout = kwargs.get('timeout', SSH_CONNECT_TIMEOUT)

        deploy_error = None

        for username in ([ssh_username] + ssh_alternate_usernames):
            try:
                self._connect_and_run_deployment_script(
                    task=kwargs['deploy'], node=node,
                    ssh_hostname=ip_addresses[0], ssh_port=ssh_port,
                    ssh_username=username, ssh_password=password,
                    ssh_key_file=ssh_key_file, ssh_timeout=ssh_timeout,
                    timeout=timeout, max_tries=max_tries)
            except Exception:
                # Try alternate username
                # Todo: Need to fix paramiko so we can catch a more specific
                # exception
                e = sys.exc_info()[1]
                deploy_error = e
            else:
                # Script sucesfully executed, don't try alternate username
                deploy_error = None
                break

        if deploy_error is not None:
            raise DeploymentError(node=node, original_exception=deploy_error,
                                  driver=self)

        return node

    def _ssh_client_connect(self, ssh_client, wait_period=1.5, timeout=300):
        """
        Try to connect to the remote SSH server. If a connection times out or
        is refused it is retried up to timeout number of seconds.

        @keyword    ssh_client: A configured SSHClient instance
        @type       ssh_client: C{SSHClient}

        @keyword    wait_period: How many seconds to wait between each loop
                                 iteration (default is 1.5)
        @type       wait_period: C{int}

        @keyword    timeout: How many seconds to wait before timing out
                             (default is 600)
        @type       timeout: C{int}

        @return: C{SSHClient} on success
        """
        start = time.time()
        end = start + timeout

        while time.time() < end:
            try:
                ssh_client.connect()
            except (IOError, socket.gaierror, socket.error):
                # Retry if a connection is refused or timeout
                # occurred
                ssh_client.close()
                time.sleep(wait_period)
                continue
            else:
                return ssh_client

        raise LibcloudError(value='Could not connect to the remote SSH ' +
                            'server. Giving up.', driver=self)

    def _connect_and_run_deployment_script(self, task, node, ssh_hostname,
                                           ssh_port, ssh_username,
                                           ssh_password, ssh_key_file,
                                           ssh_timeout, timeout, max_tries):
        ssh_client = SSHClient(hostname=ssh_hostname,
                               port=ssh_port, username=ssh_username,
                               password=ssh_password,
                               key=ssh_key_file,
                               timeout=ssh_timeout)

        # Connect to the SSH server running on the node
        ssh_client = self._ssh_client_connect(ssh_client=ssh_client,
                                              timeout=timeout)

        # Execute the deployment task
        self._run_deployment_script(task=task, node=node,
                                    ssh_client=ssh_client,
                                    max_tries=max_tries)

    def _run_deployment_script(self, task, node, ssh_client, max_tries=3):
        """
        Run the deployment script on the provided node. At this point it is
        assumed that SSH connection has already been established.

        @keyword    task: Deployment task to run on the node.
        @type       task: C{Deployment}

        @keyword    node: Node to operate one
        @type       node: C{Node}

        @keyword    ssh_client: A configured and connected SSHClient instance
        @type       ssh_client: C{SSHClient}

        @keyword    max_tries: How many times to retry if a deployment fails
                               before giving up (default is 3)
        @type       max_tries: C{int}

        @return: C{Node} Node instance on success.
        """
        tries = 0
        while tries < max_tries:
            try:
                node = task.run(node, ssh_client)
            except Exception:
                e = sys.exc_info()[1]
                tries += 1
                if tries >= max_tries:
                    e = sys.exc_info()[1]
                    raise LibcloudError(value='Failed after %d tries: %s'
                                        % (max_tries, str(e)), driver=self)
            else:
                ssh_client.close()
                return node


    def ex_list_networks(self, region=None):
        """
        Overrides the 'os-networksv2' API from libcloud in favor of the
        Openstack Network Manager. We will use this until libcloud completely
        supports quantum
        """
        network_manager = NetworkManager.settings_init()
        return network_manager.listLCNetworks()

    def ex_suspend_node(self, node):
        """
        Suspend a node.
        """
        resp = self._node_action(node, 'suspend')
        return resp.status == httplib.ACCEPTED

    def ex_resume_node(self, node):
        """
        Resume a node.
        """
        resp = self._node_action(node, 'resume')
        return resp.status == httplib.ACCEPTED

    #Volumes
    def create_volume(self, **kwargs):
        """
        Create a new volume

        @keyword name: The name of the new volume
        @type    name: C{str}

        @keyword description: A description for the new volume (Optional)
        @type    description: C{str}

        @keyword size: The size of the new volume
        @type    size: C{int}
        """
        body = {'volume': {
            'display_name': kwargs.get('name', ''),
            'display_description': kwargs.get('description', ''),
            'size': kwargs.get('size', '1')
        }
        }
        server_resp = self.connection.request('/os-volumes',
                                              method='POST',
                                              data=body)
        try:
            volume_obj = self._to_volume(server_resp.object['volume'])
            return (server_resp.status == 200, volume_obj)
        except Exception, e:
            logger.exception("Exception occured creating volume")
            return (False, None)

    def list_volumes(self):
        return self._to_volumes(self.connection.request("/os-volumes").object)

    def update_volume(self, **kwargs):
        """
        """
        data_dict = {'volume': {}}
        #Add information to be updated
        if kwargs.get('display_name', None):
            data_dict['volume']['display_name'] = kwargs['display_name']
        if kwargs.get('display_description', None):
            data_dict['volume']['display_description'] =\
            kwargs['display_description']
        if kwargs.get('metadata', None):
            data_dict['volume']['metadata'] = kwargs['metadata']
        server_resp = self.connection.request('/os-volumes/%s' % kwargs['id'],
                                              method='POST',
                                              data=data_dict)
        try:
            return (server_resp.status == 200, server_resp.object['volume'])
        except Exception, e:
            logger.exception("Exception occured updating volume")
            return (False, None)

    #Volume Attachment
    def attach_volume(self, node, volume, device=None):
        """
        Attaches volume to node at device location
        """
        server_id = node.id
        volume_id = volume.id
        server_resp = self.connection.request(
            '/servers/%s/os-volume_attachments' % server_id,
            method='POST',
            data={'volumeAttachment':
                 {'volumeId': volume_id,
                  'device': device
                  }
                  })
        return server_resp

    def detach_volume(self, volume):
        """
        Detaches volume from a node
        """
        server_id = volume.attachment_set[0].get('serverId')
        volume_id = volume.id
        server_resp = self.connection.request(
            '/servers/%s/os-volume_attachments/%s' %
            (server_id, volume_id),
            method='DELETE')
        return server_resp.status == 202

    def destroy_volume(self, volume):
        """
        Destroys a single volume
        """
        volume_id = volume.id
        server_resp = self.connection.request(
            '/os-volumes/%s' % (volume_id,),
            method='DELETE')
        return server_resp.status == 202

    def ex_list_all_instances(self):
        """
        List all instances from all tenants of a user
        """
        server_resp = self.connection.request(
            '/servers/detail?all_tenants=1',
            method='GET')
        return self._to_nodes(server_resp.object)

    def ex_list_volume_attachments(self, node):
        """
        List all attached/attaching volumes for a specific node
        """
        server_id = node.id
        server_resp = self.connection.request(
            '/servers/%s/os-volume_attachments' % server_id,
            method='GET')
        return server_resp.object.get('volumeAttachments', {})

    def ex_get_volume_attachment(self, volume):
        """
        Get details for specific volume attachment on a node
        """
        server_id = volume.attachment_set[0].get('serverId')
        attachment_id = volume.attachment_set[0].get('id')
        server_resp = self.connection.request(
            '/servers/%s/os-volume_attachments/%s' %
            (server_id, attachment_id),
            method='GET')
        return server_resp.object

    #Keypairs
    def ex_create_keypair(self, **kwargs):
        """
        Create a new keypair

        @keyword public_key: The string containing the entire public key
        @type    public_key: C{str}

        @keyword name: The name of the new keypair
        @type    name: C{str}
        """
        name = kwargs.get('name', '')
        public_key = kwargs.get('public_key', '')
        logger.debug("name = %s public_key = %s" % (name, public_key))
        data = {"keypair":
               {"name": unicode(name),
                "public_key": unicode(public_key)
                }
                }
        server_resp = self.connection.request('/os-keypairs',
                                              method='POST',
                                              data=data)
        try:
            return (server_resp.status == 200,
                    server_resp.object['keypair']['fingerprint'])
        except Exception, e:
            logger.exception("Exception occured creating keypair")
            return (False, None)

    def ex_delete_keypair(self, **kwargs):
        """
        Delete an existing keypair
        """
        try:
            server_resp = self.connection.request(
                '/os-keypairs/%s' % kwargs.get('name', ''),
                method='DELETE')
            return server_resp.status == 202
        except Exception, e:
            logger.exception("Exception occured deleting keypair")
            return (False, None)

    def ex_list_keypairs(self):
        def _to_keypairs(el):
            return [keypair['keypair'] for keypair in el['keypairs']]
        return _to_keypairs(self.connection.request("/os-keypairs").object)

    def ex_hypervisor_statistics(self):
        return self.connection.request(
            "/os-hypervisors/statistics").object['hypervisor_statistics']

    #Floating IP Pool
    def ex_list_floating_ip_pools(self, **kwargs):
        """
        List all floating IP pools
        """
        def _to_ip_pools(ip_pool_list):
            return [ip_pool_obj for ip_pool_obj
                    in ip_pool_list['floating_ip_pools']]
        return _to_ip_pools(self.connection.request(
            "/os-floating-ip-pools").object)

    #Floating IPs
    def ex_list_floating_ips(self, region=None, **kwargs):
        """
        List all floating IPs in the tenants pool
        """
        def _to_ips(ip_list):
            return [floating_ip for floating_ip in ip_list['floating_ips']]
        try:
            return _to_ips(self.connection.request("/os-floating-ips").object)
        except:
            logger.warn("Unable to list floating ips from nova.")
            return []
#        network_manager = NetworkManager.lc_driver_init(self, region)
#        return network_manager.list_floating_ips()

    def ex_allocate_floating_ip(self, pool_name, **kwargs):
        """
        Allocate a new floating IP address to the tenants pool
        """
        try:
            floating_ip_obj = self.connection.request(
                '/os-floating-ips', method='POST',
                data={'pool': pool_name}).object
            return floating_ip_obj['floating_ip']
        except Exception, e:
            raise

    def ex_deallocate_floating_ip(self, floating_ip, **kwargs):
        """
        Deallocate an existing floating_ip from tenants pool
        """
        try:
            server_resp = self.connection.request(
                '/os-floating-ips/%s' % floating_ip,
                method='DELETE')
            return server_resp.object
        except Exception, e:
            raise

    def ex_associate_floating_ip(self, server, address, **kwargs):
        """
        Associate an allocated floating IP to the node
        """
        try:
            server_resp = self.connection.request(
                '/servers/%s/action' % server,
                method='POST',
                data={'addFloatingIp': {'address': address}})
            return server_resp.object
        except Exception, e:
            raise

    def ex_disassociate_floating_ip(self, server, address=None, **kwargs):
        """
        Disassociate a floating IP that's been associated to the node
        """
        try:
            if not address:
                public_ips = server.extra['addresses']['public']
                if not public_ips:
                    logger.warn("Could not determine public IP address,\
                    please provide the floating IP address")
                    return None
                address = public_ips[0]['addr']
            server_resp = self.connection.request(
                '/servers/%s/action' % server,
                method='POST',
                data={'removeFloatingIp': {'address': address}})
            return server_resp.object
        except Exception, e:
            raise

    #Security Groups
    def ex_create_security_group(self, name,
                                 description='Created by Atmosphere--Libcloud',
                                 **kwargs):
        try:
            data = {
                'security_group': {
                    'name': name,
                    'description': description
                }
            }
            server_resp = self.connection.request(
                '/os-security-groups/',
                method='POST',
                data=data)
            return server_resp.object
        except Exception, e:
            raise

    def ex_delete_security_group(self, sec_group_id, **kwargs):
        try:
            server_resp = self.connection.request(
                '/os-security-groups/%s' % sec_group_id,
                method='DELETE')
            return server_resp.object
        except Exception, e:
            raise

    def ex_list_security_groups(self, **kwargs):
        try:
            server_resp = self.connection.request(
                '/os-security-groups/',
                method='GET')
            #PARSE _to_sec_groups & to_sec_group
            return server_resp.object
        except Exception, e:
            raise

    def ex_add_security_group(self, server, sec_group, **kwargs):
        try:
            server_resp = self.connection.request(
                '/servers/%s/action' % server,
                method='POST',
                data={'addSecurityGroup': {'address': address}})
            return server_resp.object
        except Exception, e:
            raise

    def ex_remove_security_group(self, server, sec_group, **kwargs):
        try:
            server_resp = self.connection.request(
                '/servers/%s/action' % server,
                method='POST',
                data={'removeSecurityGroup': {'address': address}})
            return server_resp.object
        except Exception, e:
            raise

    #Security Group Rules
    def ex_create_security_group_rule(self, protocol, from_port,
                                      to_port, cidr, group_id,
                                      parent_group_id, **kwargs):
        try:
            server_resp = self.connection.request(
                '/os-security-group-rules',
                method='POST',
                data={"security_group_rule": {
                    "ip_protocol": protocol,
                    "from_port": from_port,
                    "to_port": to_port,
                    "cidr": cidr,
                    "group_id": group_id,
                    "parent_group_id": parent_group_id}
                })
            return server_resp.object
        except Exception, e:
            raise

    def ex_delete_security_group_rule(self, sec_group_rule_id, **kwargs):
        try:
            server_resp = self.connection.request(
                '/os-security-group-rules/%s' % sec_group_rule_id,
                method='DELETE')
            return server_resp.object
        except Exception, e:
            raise

    def ex_list_security_group_rules(self, **kwargs):
        try:
            server_resp = self.connection.request(
                '/os-security-group-rules',
                method='GET')
            #PARSE _to_sec_group_rule & to_sec_group_rule
            return server_resp.object
        except Exception, e:
            raise

    #API Limits
    def ex_get_limits(self):
        """
        _to_rate and _to_absolute
        """
        def _to_rate(el):
            rate_limits = el.get('limits', {}).get('rate', [])
            limit_dict = {}
            for a_limit in rate_limits:
                rest_dict = {}
                for rest_limit in a_limit['limit']:
                    r_limit_map = {}
                    r_limit_map['call_available'] = rest_limit['value']
                    r_limit_map['call_limit'] = rest_limit['remaining']
                    r_limit_map['duration'] = rest_limit['unit']
                    r_limit_map['limit_expiry'] = rest_limit['next-available']
                    rest_dict[rest_limit['verb']] = r_limit_map
                limit_dict[a_limit['uri']] = rest_dict
            return limit_dict

        def _to_absolute(el):
            return el.get('limits', {}).get('absolute', {})

        json_limits = self.connection.request("/limits").object
        rate = _to_rate(json_limits)
        absolute = _to_absolute(json_limits)
        return {"rate": rate, "absolute": absolute}

    """
    Private methods
    While these methods are useful,
    they will NOT be included when we push back to libcloud..
    """
    def _get_or_create_keypair(self, name, public_key):
        keypairs = self.ex_list_keypairs()
        for keypair in keypairs:
            if unicode(keypair['name']) == unicode(name):
                return keypair
        return self.ex_create_keypair(tenant_id=name,
                                      name=name,
                                      public_key=public_key)

    def _add_keypair(self, kwargs):
        """
        #TODO: Make this a generic kwarg that is POPed
        from the list (key_location, key_file, etc.)
        """
        kwargs.update({'ex_keyname': unicode(self.key)})
        public_key = open("/opt/dev/atmosphere/extras/ssh/id_rsa.pub", "r").read()
        keypair = self._get_or_create_keypair(name=unicode(self.key),
                                              public_key=public_key)
        if not keypair:
            logger.warn("No keypair for %s" % identity.json())

    def _add_floating_ip(self, server_id, region=None, *args, **kwargs):
        #Convert to celery task..
        """
        Add IP (Quantum)
        There is no good way to interface libcloud + nova + quantum,
        instead we call quantumclient directly..
        Feel free to replace when a better mechanism comes along..
        """
        network_manager = NetworkManager.lc_driver_init(self, region)
        return network_manager.associate_floating_ip(server_id)

    def _deprecated_add_floating_ip(self, server_id):
        """
        Add IP (Nova-Network -- deprecated)
        """
        floating_ip_pool = self.ex_list_floating_ip_pools()[0]
        pool_name = floating_ip_pool['name']
        floating_ip = self.ex_allocate_floating_ip(pool_name)
        logger.debug('Server:%s IP:%s' % (server_id, floating_ip['ip']))
        self.ex_associate_floating_ip(server_id, floating_ip['ip'])
