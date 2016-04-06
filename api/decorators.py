"""
Atmosphere service utils for rest api.

"""
from functools import wraps

from core.models import AtmosphereUser as User


def emulate_user(func):
    """
    Support for staff users to emulate a specific user history.

    This decorator is specifically for use with an APIView.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        emulate_name = self.request.query_params.get('username', None)
        if self.request.user.is_staff and emulate_name:
            emulate_name = emulate_name[0]  # Querystring conversion
            original_user = self.request.user
            try:
                self.request.user = User.objects.get(username=emulate_name)
                self.emulated = (True, original_user, emulate_name)
            except User.DoesNotExist:
                self.emulated = (False, original_user, emulate_name)
        return func(self, *args, **kwargs)
    return wrapper
