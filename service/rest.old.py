#
# Copyright (c) 2010, iPlant Collaborative, University of Arizona, Cold Spring Harbor Laboratories, University of Texas at Austin
# This software is licensed under the CC-GNU GPL version 2.0 or later.
# License: http://creativecommons.org/licenses/GPL/2.0/
#
# Author: Seung-jin Kim
# Contact: seungjin@email.arizona.edu
# Twitter: @seungjin
#

# atmosphere libraries
from djangorestframework.reverse import reverse
from djangorestframework.views import View
from djangorestframework.response import Response
from djangorestframework import status

from atmosphere.logger import logger
from atmosphere.service.models import Euca_Key



"""
v2 - REST Classes
"""
class ProviderCollection(View):
    """
    Represents:
        A Collection of Provider
        Calls to the Provider Class
    """
    def get(self, request):
        """
        List all providers that match USER
        """
        pass
    def post(self, request):
        """
        Create a new provider with POST credentials
        TODO: Determine if this will ever be used
        """
        pass
class Provider(View):
    """
    Represents:
        Calls to modify the single Provider
    """
    def get(self, request, provider_id):
        """
        Return the provider inofrmation
        TODO: A list of valid endpoints ?
        """
        pass
    def put(self, request, provider_id):
        """
        Update information for the provider (Meta-Information only?)
        """
        pass
    def delete(self, request, provider_id):
        """
        Remove the matching provider
        """
        pass
class IdentityCollection(View):
    """
    Represents:
        A Collection of Identity
        Calls to the Identity Class
    """
    def get(self, request, provider_id):
        """
        Collection of identity that match USER and the provider_id
        """
        pass
    def post(self, request, provider_id):
        """
        Create a new identity with POST credentials for provider_id
        """
        pass
class Identity(View):
    """
    Represents:
        Calls to modify the single Identity
    """
    def get(self, request, provider_id, identity_id):
        """
        Return the credential information for this identity
        """
        pass
    def put(self, request, provider_id, identity_id):
        """
        Update the credentials for this identity (Keeps provider the same?)
        """
        pass
    def delete(self, request, provider_id, identity_id):
        """
        Remove the credentials matching this identity
        """
        pass
class MachineCollection(View):
    """
    Represents:
        A Collection of Machine
        Calls to the Machine Class
    """
    def get(self, request, provider_id, identity_id):
        """
        Using provider and identity, getlist of machines
        """
        pass
    def post(self, request, provider_id, identity_id):
        """
        Create a new machine object (snapshot an instance? OR programmatically add new machine to DB)
        """
        pass
class Machine(View):
    """
    Represents:
        Calls to modify the single machine
    """
    def get(self, request, provider_id, identity_id, machine_id):
        """
        Lookup the machine information (Lookup using the given provider/identity)
        Update on server (If applicable)
        """
        pass
    def put(self, request, provider_id, identity_id):
        """
        Lookup the machine information (Lookup using the given provider/identity)
        Update on server (If applicable)
        THEN: Update on DB
        """
        pass
    def delete(self, request, provider_id, identity_id):
        """
        Remove the machine (Lookup using the given provider/identity)
        THEN: Remove the machine from DB
        """
        pass

class InstanceCollection(View):
    """
    Represents:
        A Collection of Instance
        Calls to the Instance Class
    """
    def get(self, request):
        """
        Returns a list of all instances
        """
        logger.warn('GET found!')
        method_params = get_request_parameters(request)
        euca_creds = Euca_Key.objects.get(username='esteve')
        api_response = service_api_request(euca_creds, {'username':'esteve'}, 'getInstanceList', method_params)
        response = HttpResponse(api_response, content_type="application/json")
        response['Cache-Control'] = 'no-cache'
        return response

    def post(self, request):
        """
        Instance Class:
        Launches an instance based on the params
        Returns a single instance
        """
        logger.warn('POST found!')
        method_params = get_request_parameters(request)
        logger.warn('launch with')
        logger.warn(method_params)
        euca_creds = Euca_Key.objects.get(username='esteve')
        api_response = service_api_request(euca_creds, {'username':'esteve'}, 'launchInstance', method_params)
        response = HttpResponse(api_response, content_type="application/json")
        response['Cache-Control'] = 'no-cache'
        logger.warn('response is')
        logger.warn(response)
        return response
class Instance(View):
    """
    Represents an instance object
    TODO: Better name!
    """
    def get(self, request, instance_id):
        """
        Return the object belonging to this instance ID
        TODO: FUTUREBUG: instance_id may not be a true key
        """
        logger.warn("GET found!")
        instances = Instance.objects.filter(instance_id=instance_id)
        if not instances:
            return HttpResponse("Instance-id does not match")
        instance = instances[0]
        response = HttpResponse(instance.json(), content_type='application/json')
        return response
    def put(self, request, instance_id):
        logger.warn("PUT found!")
        logger.warn(request)
        logger.warn("Update vars:%s " % get_request_parameters(request))
        instances = Instance.objects.filter(instance_id=instance_id)
        if not instances:
            return HttpResponse("Instance-id does not match")
        instance = instances[0]
        #make updates
        #save instance
        response = HttpResponse(instance.json(), content_type='application/json')
        return response
    def delete(self, request, instance_id):
        logger.warn("DELETE found!")
        logger.warn(request)
        instances = Instance.objects.filter(instance_id=instance_id)
        if not instances:
            return HttpResponse("Instance-id does not match")
        instance = instances[0]
        response = HttpResponse(instance.json(), content_type='application/json')
        return response

class UserCollection(View):
    """
    Represents both the collection of users
    AND
    Objects on the User class
    """
    def post(self, request):
        """
        User Class:
        Create a new user in the database
        Returns the user created or error that occurred
        """
        pass
    def get(self, request):
        """
        Returns a list of all users
        (Admin only..?)
        """
        all_users = User.objects.all()
        response = HttpResponse(all_users, content_type='application/json')
        return response

class User(View):
    def get(self, request, username):
        """
        Return the object belonging to the user as well as the 'default' provider/identity
        1. Test for authenticated username (Or if admin is the username for emulate functionality)
        2. <DEFAULT PROVIDER> Select first provider username can use
        3. <DEFAULT IDENTITY> Select first provider username can use
        4. Set in session THEN pass in response
        """
        pass
