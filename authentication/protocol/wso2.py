import jwt
import re

from base64 import b64decode
from Crypto.PublicKey import RSA
from datetime import datetime
from urlparse import urlparse

from django.contrib.auth import get_user_model
from django.conf import settings
from authentication.exceptions import Unauthorized
from authentication.protocol.jwt_oauth import JWTServiceProvider
from threepio import logger


User = get_user_model()


class WSO2_JWT(JWTServiceProvider):
    IGNORE_EXPIRY = False
    issuer = None
    prefix = ''

    def __init__(self, keyfile, issuer='wso2.org/products/am', prefix='http://wso2.org/claims'):
        self.keyfile_path = keyfile
        if issuer:
            self.issuer = issuer
        if prefix:
            self.prefix = prefix

    def decode_assertion(self, jwt_assertion):
        """
        INPUT:
        jwt_assertion - the 'JWT assertion' to be decoded (str)
        PROVIDED:
        public_key - b64 encoded public key (str)
        Output:
        message - The Assertion message (dict)
        """
        with open(self.keyfile_path,'r') as the_file:
            public_key = the_file.read()
        try:
            decoded_pubkey = b64decode(public_key)
            rsa_key = RSA.importKey(decoded_pubkey)
            pem_rsa = rsa_key.exportKey()
            decoded_assertion = jwt.decode(jwt_assertion, pem_rsa)
            logger.debug(decoded_assertion)
            return decoded_assertion
        except Exception:
            logger.exception("Could not decode JWT Assertion <%s>." % jwt_assertion)
            raise Unauthorized("Could not decode JWT Assertion <%s>." % jwt_assertion)

    def validate_assertion(self, decoded_assertion):
        expires_key = "exp"
        username_key = "%s/enduser" % self.prefix

        issuer = decoded_assertion.get('iss')
        role = decoded_assertion.get('%s/role' % self.prefix)
        username = decoded_assertion.get(username_key)
        expire_epoch_ms = decoded_assertion.get(expires_key)

        if issuer != self.issuer:
            raise Unauthorized("Unexpected Issuer: %s Expected: %s" % (issuer, self.issuer))

        if not username:
            raise Unauthorized("Decoded message is missing Key %s" % username_key)

        if not expire_epoch_ms and not self.IGNORE_EXPIRY:
            raise Unauthorized("Decoded message is missing Key %s" % expires_key)

        # TEST #1 - Timestamps are current
        if self.IGNORE_EXPIRY:
            token_expires = None
        else:
            token_expires = datetime.fromtimestamp(expire_epoch_ms/1000)
            now_time = datetime.now()
            if token_expires <= now_time:
                raise Unauthorized("Token is EXPIRED as of %s" % token_expires)

        # TEST #2 -  Ensure user existence in the correct group
        if 'everyone' not in role:
            raise Unauthorized("User %s does not have the correct 'role'. Expected '%s' "
                    % (username, 'everyone'))

        # TEST #3 - Strip the name and ensure that the user exists
        username = self._strip_wso2_username(username)
        user = User.objects.filter(username=username)
        if not user:
            raise Unauthorized("Username %s does not yet exist as a User object -- Please create your account FIRST."
                               % username)
        user = user.get()
        #TODO: Update the users attributes using the decoded_assertion!

        return user, token_expires

    def _strip_wso2_username(self, username):
        regexp = re.search(r'agavedev\/(.*)@', username)
        username =  regexp.group(1)

        # NOTE: REMOVE this when it is no longer true!
        # Force any username lookup to be in lowercase
        username = username.lower()
        return username
