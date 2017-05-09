class DefaultQuotaPlugin(object):
    def get_default_quota(self, user, provider):
        raise NotImplementedError("Validation plugins must implement a get_default_quota function that "
                                  "takes two arguments: 'user' and 'provider")
