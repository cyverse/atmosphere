from jetstream.tasks import xsede_tacc_map
from jetstream.allocation import get_project_allocations


def validate_account(username):
    """
    Validates an account based on the business logic assigned by jetstream.
    In this example:
    * Accounts are *ONLY* valid if they have 1+ 'jetstream' allocations.
    * All other allocations are ignored.
    """
    tacc_username = xsede_tacc_map(username)
    project_allocations = get_project_allocations(tacc_username)
    if not project_allocations:
        return False
    return True


def assign_allocation(username):
    """
    Assign allocation based on the information you know about the user
    """
    pass
