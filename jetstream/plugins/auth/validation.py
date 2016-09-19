from jetstream.allocation import TASAPIDriver
from jetstream.exceptions import TASAPIException

from atmosphere.plugins.auth.validation import ValidationPlugin
from threepio import logger

class XsedeProjectRequired(ValidationPlugin):
    def validate_user(self, user):
        """
        Validates an account based on the business logic assigned by jetstream.
        In this example:
        * Accounts are *ONLY* valid if they have 1+ 'jetstream' allocations.
        * All other allocations are ignored.
        """
        tas_driver = TASAPIDriver()
        try:
            tacc_username = tas_driver.get_tacc_username(user)
            project_allocations = tas_driver.get_user_allocations(tacc_username)
            if not project_allocations:
                return False
            return True
        except TASAPIException:
            logger.exception("Could not validate user: %s" % user)
            return False


def assign_allocation(username):
    """
    Assign allocation sources based on the information you know about the user?
    Or delete this :)
    """
    pass
