from django_cyverse_auth.protocol.ldap import is_user_in_group as ldap_group_search


class ValidationPlugin(object):
    def validate_user(self, user):
        raise NotImplementedError("Validation plugins must implement a validate_user function that takes a single argument: 'user'")


class AlwaysAllow(ValidationPlugin):
    """
    Given an AtmosphereUser, ensure that this user is (still?) valid.
    """
    def validate_user(self, user):
        return True


class LDAPGroupRequired(ValidationPlugin):
    """
    For CyVerse, LDAP Validation via 'atmo-user' is how we test
    """
    def __init__(self, *args, **kwargs):
        #TODO: Possibly introduce setting for which ldap group to search, sensible default == 'atmo-user'?
        pass

    def validate_user(self, user):
        #FIXME: When others start using LDAP for validation, this may be more helpful as a setting.
        #       alternatively, this may belong in `/cyverse/plugins`?
        return ldap_group_search(user.username, 'atmo-user')
