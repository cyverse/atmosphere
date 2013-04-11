"""
Atmosphere service driver.

Driver classes define interfaces and implement functionality using providers.
"""

from abc import ABCMeta, abstractmethod
from datetime import datetime
import sys
import time

from libcloud.compute.deployment import ScriptDeployment
from libcloud.compute.deployment import MultiStepDeployment
from libcloud.compute.types import DeploymentError

from atmosphere import settings
from atmosphere.logger import logger

from core.email import send_instance_email
from core.exceptions import MissingArgsException, ServiceException

from service.provider import AWSProvider
from service.provider import EucaProvider
from service.provider import OSProvider

from service.identity import AWSIdentity
from service.identity import EucaIdentity
from service.identity import OSIdentity

from service.mixins.driver import APIFilterMixin, MetaMixin,\
    TaskMixin, InstanceActionMixin


class BaseDriver():
    """
    BaseDriver lists a basic set of expected functionality for an esh-driver.
    Abstract class - Should not be instantiated!!
    """

    __metaclass__ = ABCMeta

    _connection = None

    identity = None

    provider = None

    identityCls = None

    providerCls = None

    @abstractmethod
    def __init__(self, identity, provider):
        raise NotImplementedError

    @abstractmethod
    def list_instances(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def list_machines(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def list_sizes(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def list_locations(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def create_instance(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def deploy_instance(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def reboot_instance(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def destroy_instance(self, *args, **kwargs):
        raise NotImplementedError

    def resume_instance(self, *args, **kwargs):
        raise NotImplementedError

    def suspend_instance(self, *args, **kwargs):
        raise NotImplementedError

    def resize_instance(self, *args, **kwargs):
        raise NotImplementedError

class VolumeDriver():
    """
    VolumeDriver provides basic storage volume functionality for libcloud
    or esh-drivers.
    Abstract class - Should not be instantiated!!
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def list_volumes(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def create_volume(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def destroy_volume(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def attach_volume(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def detach_volume(self, *args, **kwargs):
        raise NotImplementedError


class LibcloudDriver(BaseDriver, VolumeDriver, APIFilterMixin):
    """
    Provides direct access to the libcloud methods and data.
    """

    def __init__(self, provider, identity):
        if provider is None or identity is None:
            raise MissingArgsException(
                'LibcloudDriver is Missing Required Identity and/or Provider.')
        self.identity = identity
        self.provider = provider
        self._connection = self.provider.get_driver(self.identity)

    def list_instances(self, *args, **kwargs):
        return self._connection.list_nodes()

    def list_machines(self, *args, **kwargs):
        return self._connection.list_images()

    def list_sizes(self, *args, **kwargs):
        return self._connection.list_sizes()

    def list_locations(self, *args, **kwargs):
        return self._connection.list_locations()

    def create_instance(self, *args, **kwargs):
        return self._connection.create_node(*args, **kwargs)

    def deploy_instance(self, *args, **kwargs):
        return self._connection.deploy_node(*args, **kwargs)

    def reboot_instance(self, *args, **kwargs):
        return self._connection.reboot_node(*args, **kwargs)

    def destroy_instance(self, *args, **kwargs):
        return self._connection.destroy_node(*args, **kwargs)

    def list_volumes(self, *args, **kwargs):
        return self._connection.list_volumes(*args, **kwargs)

    def create_volume(self, *args, **kwargs):
        return self._connection.create_volume(*args, **kwargs)

    def destroy_volume(self, *args, **kwargs):
        return self._connection.destroy_volume(*args, **kwargs)

    def attach_volume(self, *args, **kwargs):
        return self._connection.attach_volume(*args, **kwargs)

    def detach_volume(self, *args, **kwargs):
        return self._connection.detach_volume(*args, **kwargs)


class EshDriver(LibcloudDriver, MetaMixin):
    """
    """

    def __init__(self, provider, identity):
        super(EshDriver, self).__init__(provider, identity)
        if not(isinstance(provider, self.providerCls)
           and isinstance(identity, self.identityCls)):
            raise ServiceException('Wrong Provider or Identity')

    def list_instances(self, *args, **kwargs):
        """
        Return the InstanceClass representation of a libcloud node
        """
        return self.provider.instanceCls.get_instances(
            super(EshDriver, self).list_instances())

    def list_machines(self, *args, **kwargs):
        """
        Return the MachineClass representation of a libcloud NodeImage
        """
        return self.provider.machineCls.get_machines(
            super(EshDriver, self).list_machines)

    def list_sizes(self, *args, **kwargs):
        """
        Return the SizeClass representation of a libcloud NodeSize
        """
        return self.provider.sizeCls.get_sizes(
            super(EshDriver, self).list_sizes)

    def list_locations(self, *args, **kwargs):
        return super(EshDriver, self).list_locations()

    def create_instance(self, *args, **kwargs):
        """
        Return the InstanceClass representation of a libcloud node
        """
        logger.debug(str(args))
        logger.debug(str(kwargs))
        return self.provider.instanceCls(
            super(EshDriver, self).create_instance(*args, **kwargs))

    def deploy_instance(self, *args, **kwargs):
        return self.provider.instanceCls(
            super(EshDriver, self).deploy_instance(*args, **kwargs))

    def reboot_instance(self, *args, **kwargs):
        return super(EshDriver, self).reboot_instance(*args, **kwargs)

    def resume_instance(self, *args, **kwargs):
        return super(EshDriver, self).resume_instance(*args, **kwargs)

    def suspend_instance(self, *args, **kwargs):
        return super(EshDriver, self).suspend_instance(*args, **kwargs)

    def destroy_instance(self, *args, **kwargs):
        return super(EshDriver, self).destroy_instance(*args, **kwargs)

    def list_volumes(self, *args, **kwargs):
        return self.provider.volumeCls.get_volumes(
            super(EshDriver, self).list_volumes(*args, **kwargs))

    def create_volume(self, *args, **kwargs):
        return super(EshDriver, self).create_volume(*args, **kwargs)

    def destroy_volume(self, *args, **kwargs):
        return super(EshDriver, self).destroy_volume(*args, **kwargs)

    def attach_volume(self, *args, **kwargs):
        return super(EshDriver, self).attach_volume(*args, **kwargs)

    def detach_volume(self, *args, **kwargs):
        return super(EshDriver, self).detach_volume(*args, **kwargs)


class OSDriver(EshDriver, InstanceActionMixin, TaskMixin):
    """
    """
    providerCls = OSProvider

    identityCls = OSIdentity

    def __init__(self, provider, identity):
        super(OSDriver, self).__init__(provider, identity)
        self._connection.connection.service_region =\
            settings.OPENSTACK_DEFAULT_REGION

    def eventual_deploy_instance(self, *args, **kwargs):
        pass

    def deploy_init_to(self, *args, **kwargs):
        if args:
            instance = args[0]
        else:
            raise MissingArgsException("Missing instance argument.")
        username = self.identity.user.username
        atmo_init = "/usr/sbin/atmo_init_full.py"
        server_atmo_init = "/init_files/30/atmo-init-full.py"
        script_deps = ScriptDeployment(
            "apt-get update;apt-get install -y emacs vim wget language-pack-en"
            + " make gcc g++ gettext texinfo autoconf automake")
        script_wget = ScriptDeployment("wget -O %s %s%s" %
                                       (atmo_init, settings.SERVER_URL,
                                           server_atmo_init))
        script_chmod = ScriptDeployment("chmod a+x %s" % atmo_init)
        instance_token = kwargs.get('token', '')
        awesome_atmo_call = "%s --service_type=%s --service_url=%s"
        awesome_atmo_call += " --server=%s --user_id=%s --token=%s"
        awesome_atmo_call += " --vnc_license=%s"
        awesome_atmo_call %= (
            atmo_init,
            "instance_service_v1",
            settings.INSTANCE_SERVICE_URL,
            settings.SERVER_URL,
            username,
            instance_token,
            settings.ATMOSPHERE_VNC_LICENSE)
        logger.debug(awesome_atmo_call)
        str_awesome_atmo_call = str(awesome_atmo_call)
        #kludge: weirdness without the str cast...
        logger.debug(isinstance(str_awesome_atmo_call, basestring))
        script_atmo_init = ScriptDeployment(str_awesome_atmo_call)
        private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        msd = MultiStepDeployment([script_deps,
                                   script_wget,
                                   script_chmod,
                                   script_atmo_init])
        kwargs.update({'ssh_key': private_key})
        kwargs.update({'deploy': msd})
        kwargs.update({'timeout': 120})
        try:
            self.deploy_to(instance, *args, **kwargs)
        except DeploymentError as de:
            logger.error(sys.exc_info())
            logger.error(de.value)
            #raise(de)
            return False
        created = datetime.strptime(instance.extra['created'], "%Y-%m-%dT%H:%M:%SZ")
        send_instance_email(username, instance.id, instance.ip, created, username)

        return True

    def deploy_to(self, *args, **kwargs):
        """
        Deploy to an instance.
        """
        if args:
            instance = args[0]
        else:
            raise MissingArgsException("Missing instance argument.")
        if not kwargs.get('deploy'):
            raise MissingArgsException("Missing deploy argument.")
        username = self.identity.user.username
        private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        kwargs.update({'ssh_key': private_key})
        kwargs.update({'timeout': 120})
        try:
            self._connection.ex_deploy_to_node(instance._node,
                                               *args, **kwargs)
        except DeploymentError as de:
            logger.error(sys.exc_info())
            logger.error(de.value)
            return False
        return True

    def deploy_instance(self, *args, **kwargs):
        """
        Deploy instance.

        NOTE: This is blocking and uses the blocking create_node.
        """
        if not kwargs.get('deploy'):
            raise MissingArgsException("Missing deploy argument.")
        username = self.identity.user.username
        private_key = "/opt/dev/atmosphere/extras/ssh/id_rsa"
        kwargs.update({'ssh_key': private_key})
        kwargs.update({'timeout': 120})
        try:
            self.deploy_node(*args, **kwargs)
        except DeploymentError as de:
            logger.error(sys.exc_info())
            logger.error(de.value)
            return False
        return True

    def destroy_instance(self, *args, **kwargs):
        node_destroyed = self._connection.destroy_node(*args, **kwargs)
        time.sleep(5)
        self._remove_unused_floating_ips() # TODO: Add to queue to do asynchronously.
        return node_destroyed

    def suspend_instance(self, *args, **kwargs):
        return self._connection.ex_suspend_node(*args, **kwargs)

    def resume_instance(self, *args, **kwargs):
        return self._connection.ex_resume_node(*args, **kwargs)

    def resize_instance(self, *args, **kwargs):
        return self._connection.ex_resize(*args, **kwargs)

    def reboot_instance(self, *args, **kwargs):
        return self._connection.reboot_node(*args, **kwargs)

    def confirm_resize_instance(self, *args, **kwargs):
        return self._connection.ex_confirm_resize(*args, **kwargs)

    def revert_resize_instance(self, *args, **kwargs):
        return self._connection.ex_revert_resize(*args, **kwargs)

    def _add_floating_ip(self, instance_id, *args, **kwargs):
        return self._connection._add_floating_ip(instance_id, *args, **kwargs)

    def _remove_unused_floating_ips(self):
        for f_ip in self._connection.ex_list_floating_ips():
            if not f_ip.get('instance_id'):
                self._connection.ex_deallocate_floating_ip(f_ip['id'])
                logger.info("Removed unused Floating IP: %s" % f_ip)


class AWSDriver(EshDriver):
    """
    """
    providerCls = AWSProvider

    identityCls = AWSIdentity

    def deploy_instance(self, *args, **kwargs):
        """
        Deploy an AWS node.
        """
        username = self.identity.user.username
        atmo_init = "/usr/sbin/atmo_init_full.py"
        server_atmo_init = "/init_files/30/atmo-init-full.py"
        script_deps = ScriptDeployment(
            "sudo apt-get install -y emacs vim wget")
        script_wget = ScriptDeployment(
            "sudo wget -O %s %s%s" %
            (atmo_init, settings.SERVER_URL, server_atmo_init))
        script_chmod = ScriptDeployment("sudo chmod a+x %s" % atmo_init)
        instance_token = kwargs.get('token', '')
        awesome_atmo_call = "sudo %s --service_type=%s --service_url=%s"
        awesome_atmo_call += " --server=%s --user_id=%s --token=%s"
        awesome_atmo_call %= (
            atmo_init,
            "instance_service_v1",
            settings.INSTANCE_SERVICE_URL,
            settings.SERVER_URL,
            username,
            instance_token)
        logger.debug(awesome_atmo_call)
        str_awesome_atmo_call = str(awesome_atmo_call)
        #kludge: weirdness without the str cast...
        logger.debug(isinstance(str_awesome_atmo_call, basestring))
        script_atmo_init = ScriptDeployment(str_awesome_atmo_call)
        private_key = ("/opt/dev/atmosphere/extras/ssh/id_rsa")
        scripts = [script_deps,
                   script_wget,
                   script_chmod,
                   script_atmo_init]
        for s in scripts:
            logger.debug(s.name)
            s.name = s.name.replace('/root', '/home/ubuntu')
            logger.debug(s.name)
        msd = MultiStepDeployment(scripts)
        kwargs.update({'ex_keyname': 'dalloway-key'})
        kwargs.update({'ssh_username': 'ubuntu'})
        kwargs.update({'ssh_key': private_key})
        kwargs.update({'deploy': msd})
        kwargs.update({'timeout': 400})

        instance = super(AWSDriver, self).deploy_instance(*args, **kwargs)
        created = datetime.strptime(instance.extra['created'], "%Y-%m-%dT%H:%M:%SZ")
        send_instance_email(username, instance.id, instance.ip, created, username)

        return instance

    def filter_machines(self, machines, black_list=[]):
        """
        Filtered machines:
            Keep the machine if it does NOT match any word in the black_list
        """
        def _filter_machines(ms, cond):
            return [m for m in ms if cond(m)]
        black_list.extend(['bitnami', 'kernel', 'microsoft', 'Windows'])
        filtered_machines = super(AWSDriver, self).filter_machines(
            machines, black_list)
        filtered_machines = _filter_machines(
            filtered_machines,
            lambda(m): any(word in m.alias
                           for word in ['aki-', 'ari-']))
        filtered_ubuntu = _filter_machines(
            filtered_machines,
            lambda(m): any(word == m._image.extra['ownerid']
                           for word in ['099720109477']))
#        filtered_ubuntu = [machine for machine in filtered_machines
#        if any(word == machine._image.extra['ownerid'] for word in
#        ['099720109477'])]
        filtered_amazon = _filter_machines(
            filtered_machines,
            lambda(m): any(word == m._image.extra['owneralias']
                           for word in ['amazon', 'aws-marketplace']))
        filtered_ubuntu.extend(filtered_amazon)
        return filtered_ubuntu  # [-400:] #return filtered[-400:]

    def create_volume(self, *args, **kwargs):
        if 'description' in kwargs:
            kwargs.pop('description')
        return super(EshDriver, self).create_volume(*args, **kwargs)


class EucaDriver(EshDriver):
    """
    """
    providerCls = EucaProvider

    identityCls = EucaIdentity

    def deploy_instance(self, *args, **kwargs):
        raise NotImplementedError

    def resume_instance(self, *args, **kwargs):
        raise NotImplementedError

    def suspend_instance(self, *args, **kwargs):
        raise NotImplementedError
