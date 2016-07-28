from jetstream.tasks import xsede_tacc_map
from jetstream.allocation import get_project_allocations

#FIXME: move this import somewhere else? feels weird.
from atmosphere.plugins.auth.validation import ValidationPlugin

class XsedeProjectRequired(ValidationPlugin):
    def validate_user(self, user):
        """
        Validates an account based on the business logic assigned by jetstream.
        In this example:
        * Accounts are *ONLY* valid if they have 1+ 'jetstream' allocations.
        * All other allocations are ignored.
        """
        username = user.username
        tacc_username = xsede_tacc_map(username)
        project_allocations = get_project_allocations(tacc_username)
        if not project_allocations:
            return False
        return True


def assign_allocation(username):
    """
    Assign allocation sources based on the information you know about the user?
    Or delete this :)
    """
    pass
