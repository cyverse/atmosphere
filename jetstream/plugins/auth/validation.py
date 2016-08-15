from jetstream.allocation import TASAPIDriver


def validate_account(username):
    """
    Validates an account based on the business logic assigned by jetstream.
    In this example:
    * Accounts are *ONLY* valid if they have 1+ 'jetstream' allocations.
    * All other allocations are ignored.
    """
    tas_driver = TASAPIDriver()
    tacc_username = tas_driver.get_username_from_xsede(username)
    project_allocations = tas_driver.get_project_allocations(tacc_username)
    if not project_allocations:
        return False
    return True


def assign_allocation(username):
    """
    Assign allocation based on the information you know about the user
    """
    pass
