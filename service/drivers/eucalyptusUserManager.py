"""
UserManager:
    Remote Eucalyptus Admin controls..

User, BooleanField, StringList
    These XML parsing classes belong to euca_admin.py,
    and can be found on the Cloud Controller
"""
import sys
import boto
from boto.ec2.regioninfo import RegionInfo
from boto.exception import EC2ResponseError

from urlparse import urlparse
from threepio import logger

#Enter euca admin credentials here!
EUCA_ADMIN_KEY = ""
EUCA_ADMIN_SECRET = ""
EUCA_EC2_URL = ""


class UserManager():
    """
    Accessing Eucalyptus' Admin panel works
    just like any other EC2-compliant query
    HOWEVER, the default path for admin is
    '/services/Accounts/' instead of '/services/Eucalyptus'!
    """
    admin_key = None
    admin_secret = None
    admin_ec2_url = None
    account_path = None
    connection = None

    def __init__(self, *args, **kwargs):
        key = kwargs.get('key','')
        secret = kwargs.get('secret','')
        url = kwargs.get('url','')
        path = kwargs.get('account_path','/services/Accounts')

        self.admin_key = key
        self.admin_secret = secret
        self.admin_ec2_url = url
        self.account_path = path

        parsed = urlparse(url)
        region = RegionInfo(None, 'eucalyptus', parsed.hostname)
        self.connection = boto.connect_ec2(
            aws_access_key_id=self.admin_key,
            aws_secret_access_key=self.admin_secret,
            is_secure=False, region=region,
            port=parsed.port, path=self.account_path)
        self.connection.APIVersion = 'eucalyptus'

    def delete_user(self, username):
        """
        Deletes 'username' from eucalyptus,
        returns True on success
        """
        try:
            reply = self.connection.get_object(
                'DeleteUser', {'UserName': username}, BooleanResponse)
        except EC2ResponseError:
            logger.info("User does not exist")
            return False

        return reply and reply.reply == 'true'

    def add_user(self, username, email="N/A", adminUser=False):
        """
        Adds new user, with 'username' and 'email' to eucalyptus.
        returns True on success
        """
        reply = self.connection.get_object(
            'AddUser', {'UserName': username, 'Email': email,
                        'Admin': adminUser}, BooleanResponse)
        return reply and reply.reply == 'true'

    def get_keys(self, userList):
        """
        Returns a dictionary of keys for each username in userList
        """
        userDict = self.get_users(userList)
        user_keys_dict = {}
        for username in userDict.keys():
                userObj = userDict[username]
                user_keys_dict[username] = {
                    'username': username,
                    'access_key': userObj['access_key'],
                    'secret_key': userObj['secret_key']}
        return user_keys_dict

    def get_users(self, userList):
        """
        Returns a dictionary of username:attributes
        """
        params = {}
        self.connection.build_list_params(params, userList, 'UserNames')
        euca_list = self.connection.get_list(
            'DescribeUsers', params, [('euca:item', User)])
        return self.userListDict(euca_list)

    def userListDict(self, euca_list):
        """
        Utility method to turn a user_list
        (XML Parsed object from euca_admin) into python dict
        """
        userDict = {}
        for user in euca_list:
		logger.info(user.__dict__)
                userDict[user.user_userName] = {
                    'username': user.user_userName,
                    'access_key': user.user_accessKey,
                    'secret_key': user.user_secretKey,
                    'certificateSerial': user.user_certificateSerial,
                    'certificateCode': user.user_certificateCode,
                    'confirmationCode': user.user_confirmationCode,
                    'confirmed': user.user_confirmed,
                    'admin': user.user_admin,
                    'enabled': user.user_enabled,
                    'email': user.user_email,
                }
        return userDict

    #Useful calls you will want
    def get_key(self, username):
            return self.get_keys([username])[username]

    def get_all_users(self):
            return self.get_users([])

    def get_user(self, username):
            return self.get_users([username])[username]

#NOTE: I DO NOT OWN THE RIGHTS TO ANY OF THE CODE BELOW!
# The functions below are for used to parse the XML response
# from eucalyptus, and are placed here to avoid dependencies on euca_admin
##################


class User():
    """
    The user object stores the XML response for DescribeUsers
    This class was pulled from euca_admin/users.py
    """

    def __init__(self, userName=None, email="N/A", certificateCode=None,
                 confirmationCode=None, accessKey=None, secretKey=None,
                 confirmed=False, admin=False, enabled=False,
                 distinguishedName=None, certificateSerial=None):
        self.user_userName = userName
        self.user_email = email
        self.user_distinguishedName = distinguishedName
        self.user_certificateSerial = certificateSerial
        self.user_certificateCode = certificateCode
        self.user_confirmationCode = confirmationCode
        self.user_accessKey = accessKey
        self.user_secretKey = secretKey
        self.user_confirmed = confirmed
        self.user_admin = admin
        self.user_enabled = enabled
        self.user_groups = StringList()
        self.user_revoked = StringList()
        self.user_list = self.user_groups
        self.euca = None

    def __repr__(self):
        r = 'USER\t\t%s\t%s%s\t%s' \
            % (self.user_userName, self.user_email,
               '\tADMIN' if self.user_admin == 'true' else ' ',
               'ENABLED' if self.user_enabled == 'true' else 'DISABLED')
        r = '%s\nUSER-GROUP\t%s\t%s' \
            % (r, self.user_userName, self.user_groups)
        r = '%s\nUSER-CERT\t%s\t%s\t%s' \
            % (r, self.user_userName, self.user_distinguishedName,
               self.user_certificateSerial)
        r = '%s\nUSER-KEYS\t%s\t%s\t%s' \
            % (r, self.user_userName, self.user_accessKey, self.user_secretKey)
        r = '%s\nUSER-CODE\t%s\t%s' \
            % (r, self.user_userName, self.user_certificateCode)
        r = '%s\nUSER-WEB \t%s\t%s' \
            % (r, self.user_userName, self.user_confirmationCode)
        return r

    def startElement(self, name, attrs, connection):
        if name == 'euca:groups':
            return self.user_groups
        elif name == 'euca:revoked':
            return self.user_revoked
        else:
            return None

    def endElement(self, name, value, connection):
        if name == 'euca:userName':
            self.user_userName = value
        elif name == 'euca:email':
            self.user_email = value
        elif name == 'euca:admin':
            self.user_admin = value
        elif name == 'euca:confirmed':
            self.user_confirmed = value
        elif name == 'euca:enabled':
            self.user_enabled = value
        elif name == 'euca:distinguishedName':
            self.user_distinguishedName = value
        elif name == 'euca:certificateSerial':
            self.user_certificateSerial = value
        elif name == 'euca:certificateCode':
            self.user_certificateCode = value
        elif name == 'euca:confirmationCode':
            self.user_confirmationCode = value
        elif name == 'euca:accessKey':
            self.user_accessKey = value
        elif name == 'euca:secretKey':
            self.user_secretKey = value
        elif name == 'euca:entry':
            self.user_list.append(value)
        else:
            setattr(self, name, value)


class BooleanResponse:
    """
    XML Parsing class for add/delete user
    Pulled from euca_admin/generic.py
    """
    def __init__(self, reply=False):
        self.reply = reply
        self.error = None

    def __repr__(self):
        if self.error:
            print 'RESPONSE %s' % self.error
            sys.exit(1)
        else:
            return 'RESPONSE %s' % self.reply

    def startElement(self, name, attrs, connection):
        return None

    def endElement(self, name, value, connection):
        if name == 'euca:_return':
            self.reply = value
        elif name == 'Message':
            self.error = value
        else:
            setattr(self, name, value)


class StringList(list):
    """
    XML Parsing class for list of users in describeUser
    Pulled from euca_admin/generic.py
    """
    def __repr__(self):
        r = ""
        for i in self:
            r = "%s %s" % (r, i)
        return r

    def startElement(self, name, attrs, connection):
        pass

    def endElement(self, name, value, connection):
        if name == 'euca:entry':
            self.append(value)
