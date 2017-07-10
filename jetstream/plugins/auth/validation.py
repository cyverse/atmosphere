import core.models
from jetstream.allocation import TASAPIDriver, fill_user_allocation_source_for
from jetstream.exceptions import TASAPIException, NoTaccUserForXsedeException, NoAccountForUsernameException

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
        driver = TASAPIDriver()
        try:
            project_allocations = fill_user_allocation_source_for(driver, user)
            if not project_allocations:
                return False
            return True
        except (NoTaccUserForXsedeException, NoAccountForUsernameException) as e:
            logger.exception('User is invalid: %s', user)
            return False
        except TASAPIException:
            logger.exception('Some other error happened while trying to validate user: %s', user)
            active_allocation_count = core.models.UserAllocationSource.objects.filter(user=user).count()
            # TODO: Also check that:
            # - the start date of the allocation source is in the past, and
            # - the end date of the allocation source is not set, or is in the future.
            logger.debug('user: %s, active_allocation_count: %d', active_allocation_count, user)
            return active_allocation_count > 0


def assign_allocation(username):
    """
    Assign allocation sources based on the information you know about the user?
    Or delete this :)
    """
    pass
