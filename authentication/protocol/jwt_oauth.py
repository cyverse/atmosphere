from abc import ABCMeta, abstractmethod
from authentication.models import create_token


class JWTServiceProvider():
    """
    JWT Assertions come in all flavors
    This 'mapping' will give each SP a chance to implement:
    decode_assertion() - Use whatever means necessary to move from (Raw, Encoded) jwt_assertion
                         to a python dict with 'standard' keys (See WSO2)
    validate_assertion() - look at your decoded_assertion (dict)
    and determine its validity using any means necessary

    """
    __metaclass__ = ABCMeta

    issuer_key = 'iss'
    issuer = None

    def create_token_from_jwt(self, jwt_assertion):
        """
        This method point represents the 'entry point'
        """
        decoded_assertion = self.decode_assertion(jwt_assertion)
        user, expiration = self.validate_assertion(decoded_assertion)
        auth_token = create_token(user.username, expiration)
        return auth_token

    @abstractmethod
    def decode_assertion(self, jwt_assertion):
        """
        decode_assertion() - Use whatever means necessary to move from (Raw, Encoded) jwt_assertion
                             to a python dict with 'standard' keys (See WSO2)
        """
        raise NotImplemented

    @abstractmethod
    def validate_assertion(self, decoded_assertion):
        """
        validate_assertion() - look at your decoded_assertion (dict)
        and determine its validity using any means necessary
        """
        raise NotImplemented
