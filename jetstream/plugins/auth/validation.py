from django.db.models import Q
from threepio import logger

from jetstream.allocation import TASAPIDriver, fill_user_allocation_source_for
from jetstream.exceptions import TASAPIException, NoTaccUserForXsedeException, NoAccountForUsernameException
from atmosphere.plugins.auth.validation import ValidationPlugin
from core.models import UserAllocationSource
from core.query import only_current_user_allocations


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
            active_allocation_count = UserAllocationSource.objects.filter(
                only_current_user_allocations() & Q(user=user)).count()
            logger.debug('user: %s, active_allocation_count: %d', user, active_allocation_count)
            return active_allocation_count > 0
