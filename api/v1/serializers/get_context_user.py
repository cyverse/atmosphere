from django.contrib.auth.models import AnonymousUser
from core.models.user import AtmosphereUser


def get_context_user(serializer, kwargs, required=False):
    context = kwargs.get('context', {})
    user = context.get('user')
    request = context.get('request')
    if not user and not request:
        print_str = "%s was initialized"\
                    " without appropriate context."\
                    " Sometimes, like on imports, this is normal."\
                    " For complete results include the \"context\" kwarg,"\
                    " with key \"request\" OR \"user\"."\
                    " (e.g. context={\"user\":user,\"request\":request})"\
                    % (serializer,)
        if required:
            raise Exception(print_str)
        else:
            return None
    if user:
        # NOTE: Converting str to atmosphere user is easier when debugging
        if isinstance(user, str):
            user = AtmosphereUser.objects.get(
                username=user)
        elif type(user) not in [AnonymousUser, AtmosphereUser]:
            raise Exception("This Serializer REQUIRES the \"user\" "
                            "to be of type str or AtmosphereUser")
    elif request:
        user = request.user
    #    logger.debug("%s initialized with user %s"
    #                 % (serializer, user))
    return user
