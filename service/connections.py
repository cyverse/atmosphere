from atmosphere.core.models.credential import Identity, Credential
from libcloud.compute.types import Provider as LCProvider
from libcloud.compute.providers import get_driver
from urlparse import urlparse
from atmosphere.logger import logger

CONNECTION_MAP = {
        "Amazon":ec2Conn,
        "Eucalyptus":eucalyptusConn,
        "Rackspace":rackspaceConn,
}

def getConnection(identity):
    cloud_connection = CONNECTION_MAP[identity.provider.type.name](identity.credential.all())

def ec2Conn(credential):
    Driver = get_driver(LCProvider.EC2)
    #Determine key from credential set .value
    #Determine secret from credential set .value
    connection = Driver(key, secret)
    return connection

def eucaConn(credential):
    Driver = get_driver(LCProvider.EUCALYPTUS)
    #Determine key from credential set .value
    #Determine secret from credential set .value
    #Determine ec2_url from credential set .value
    urlObj = urlparse(ec2_url)
    connection = Driver(key=key, secret=secret, host=urlObj.hostname, port=urlObj.port, path=urlObj.path, secure=False)
    return connection

def rackspaceConn(credential):
    Driver = get_driver(LCProvider.RACKSPACE)
    #Determine api from credential set .value
    #Determine user from credential set .value
    connection = Driver(user, api)
    return connection
