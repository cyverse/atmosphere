from threepio import logger
from jetstream.allocation import TASAPIDriver
from cyverse.api import GrouperDriver
from django_cyverse_auth.protocol.ldap import get_groups_for
from django.conf import settings
from service.exceptions import AccountCreationConflict

class AccountCreationPlugin(object):
    """
    Validation plugins must implement a create_accounts function that
    takes two  arguments:
    - `provider (core.models.Provider)`
    - `user (core.models.AtmosphereUser)`
    Plugins are responsible for implementing `get_credentials_list`.
    The list of credentials are fed into the AccountDriver
    The accounts are created based on those credentials
    and a list of new `core.models.Identity` are returned
    """

    # Useful methods called from above..
    def find_accounts(self, provider, account_user, group_name, username, project_name, **kwargs):
        from core.models import GroupMembership, Identity
        from core.query import contains_credential
        member = GroupMembership.objects.filter(
            user__username=account_user,
            group__name=group_name)
        if not member:
            return Identity.objects.none()

        group = member.first().group
        return group.identities.filter(
                contains_credential('ex_project_name', project_name),
                provider=provider
            ).filter(
                contains_credential('key', username)
            )


class DirectOpenstackAccount(AccountCreationPlugin):
    """
    Use this Account Creation Plugin if you are using an
    "Unmanaged atmosphere" and having users login directly
    with username/password

    In the current authentication flow for "direct logins":
    - User will POST credentials to /auth, which is verified by Openstack
    - On success, (if in troposphere), call /login to record the credentials in your browser session
    - On success, call /token_update to create an openstack association using `username` and `token` (Does not save password)
    - Based on this, Account Creation here should _lookup_ the identity thats been created above, and do any final associations

    This plugin will simply verify that the above has been completed, and ensure an Allocation Source has been created.
	    - To disable Allocation sources, set compute_allowed to -1
    """
    def create_accounts(self, provider, username, force=False):
        from core.models import Identity, Project
        from core.plugins import AllocationSourcePluginManager
        identities = Identity.objects.filter(provider=provider, created_by__username=username)
        if not identities.count():
            raise AccountCreationConflict("Expected an identity to have been created for %s on Provider %s during the /token_update method. Contact support for help!" % (username, provider))
        for identity in identities:
            user = identity.created_by
            try:
                has_allocations = AllocationSourcePluginManager.ensure_user_allocation_sources(user)
                if not has_allocations:
                    raise ValueError('User "{}" has no valid allocations'.format(user))
            except Exception as e:
                logger.exception('Encountered error while ensuring user has valid Allocation Sources: "%s"', user)
                raise AccountCreationConflict(
                    'AccountDriver is trying to create an account: {} '
                    'but while ensuring user has valid Allocation Sources there was a problem: {}'.format(user, e))
            if settings.AUTO_CREATE_NEW_PROJECTS:
                project_name = identity.project_name()
                projects = Project.objects.filter(created_by=user, name=project_name)
                has_projects = projects.count() > 0
                membership = user.memberships.first()
                if not has_projects and membership:
                    group = membership.group
                    logger.info('Creating new project for %s: "%s"', user, project_name)
                    project = Project.objects.create(
                        name=project_name,
                        created_by=user,
                        owner=group,
                        description="Auto-created project for %s" % project_name)

        return identities




class AtmosphereAccountCreationPlugin(AccountCreationPlugin):
    """
    Use this Account Creation Plugin if
     you are using a "Managed atmosphere" (The default case).
     These plugins will expect username/project_name to be provided
      - Will create an account on the Openstack provider
      - Will associate the new account with the authenticated user
    """

    def get_credentials_list(self, provider, username):
        raise NotImplementedError("See docs")

    def create_accounts(self, provider, username, force=False):
        from service.driver import get_account_driver
        from core.models import Project, Identity
        credentials_list = self.get_credentials_list(provider, username)
        identities = Identity.objects.none()
        for credentials in credentials_list:
            try:
                project_name = credentials['project_name']
                created_identities = self.find_accounts(provider, **credentials)
                if created_identities and not force:
                    # logger.debug(
                    #     "Accounts already created for %s on provider %s", username, provider)
                    identities |= created_identities
                    continue
                logger.debug(
                    "Creating new account for %s with credentials - %s"
                    % (username, credentials))
                account_driver = get_account_driver(provider)
                if not account_driver:
                    raise ValueError(
                        "Provider %s produced an invalid account driver "\
                        "-- Use plugin after you create a core.Provider "\
                        "*AND* assign a core.Identity to be the core.AccountProvider."
                        % provider)
                new_identity = account_driver.create_account(**credentials)
                identities |= Identity.objects.filter(id=new_identity.id)
                memberships = new_identity.identity_memberships.filter(member__memberships__is_leader=True)
                if not memberships:
                    memberships = new_identity.identity_memberships.all()
                membership = memberships.first()
                if not membership:
                    raise ValueError("Expected at least one member in identity %s" % new_identity)
                group = membership.member
                try:
                    Project.objects.get(
                        name=project_name,
                        owner=group)
                except Project.DoesNotExist:
                    Project.objects.create(
                        name=project_name,
                        created_by=new_identity.created_by,
                        owner=group)
            except:
                logger.exception(
                    "Could *NOT* Create NEW account for %s"
                    % username)
        return identities

    def delete_accounts(self, provider, username):
        from service.driver import get_account_driver
        account_driver = get_account_driver(provider)
        if not account_driver:
            raise ValueError(
                "Provider %s produced an invalid account driver "\
                "-- Use plugin after you create a core.Provider "\
                "*AND* assign a core.Identity to be the core.AccountProvider."
                % provider)
        credentials_list = self.get_credentials_list(provider, username)
        identity_list = []
        for credentials in credentials_list:
            try:
                identities = self.find_accounts(**credentials)
                if not identities:
                    continue
                logger.debug(
                    "Removing account for %s with credentials - %s"
                    % (username, credentials))
                for identity in identities:
                    removed_identity = account_driver.delete_account(identity, **credentials)
                    identity_list.append(removed_identity)
            except:
                logger.exception(
                    "Could *NOT* delete account for %s"
                    % username)
        return identity_list


class UserGroup(AtmosphereAccountCreationPlugin):

    def get_credentials_list(self, provider, username):
        """
        For each provider:
        - 'username' and 'project_name' == username
        """
        credentials_list = []
        credentials_list.append({
            'username': username,
            'project_name': username,
            'account_user': username,
            'group_name': username,
            'is_leader': True,
        })
        return credentials_list


class GrouperPlugin(AtmosphereAccountCreationPlugin):
    """
    For CyVerse, AccountCreation respects the "Directory"
    between User and Group as described by Grouper.

    Because there are *so many* groups that exist for cyverse, we will require a whitelist
    """

    def __init__(self):
        self.driver = GrouperDriver()

    def parse_group_name(self, raw_groupname):
        name_splits = raw_groupname.split(":")
        if len(name_splits) == 5:
            return raw_groupname.split(":")[2]
        raise Exception("Could not parse the group name %s" % raw_groupname)

    def get_credentials_list(self, provider, username):
        credentials_list = []
        groups = self.driver.get_groups_for_username(username)
        for group in groups:
            new_groupname = self.parse_group_name(group['name'])
            self.driver.is_leader(group['name'], username)
            credentials_list.append({
                'account_user': username,
                'username': username,
                'project_name': new_groupname,
                'group_name': new_groupname,
                'is_leader': False,
            })
        return credentials_list


class LDAPMapper(AtmosphereAccountCreationPlugin):
    def get_credentials_list(self, provider, username):
        """
        For each provider:
        - Lookup the user on LDAP
        - Create a project for each group the user is a member of
        """
        credentials_list = []
        if settings.ENABLE_PROJECT_SHARING:
            ldap_groups = get_groups_for(username)
            for group in ldap_groups:
                credentials_list.append({
                    'account_user': username,
                    'username': username,
                    'project_name': group,
                    'group_name': group,
                    'is_leader': False,
                })
        return credentials_list


class XsedeGroup(AtmosphereAccountCreationPlugin):
    """
    For Jetstream, AccountCreation respects the "Directory"
    between User and Project.

    NOTE: This requires some communication with the TAS API Driver
    and can take some time to generate a list...
    Due to memoization, it is best to "Batch" these requests.

    For Each project listed for tacc_username(user.username):
    - 'username' == tacc_username(user.username)
    - 'project_name' == tacc_project_name
    """

    def __init__(self):
        self.tas_driver = TASAPIDriver()
        if not self.tas_driver.tacc_api:
            raise Exception("Attempting to use the XsedeGroup CreationPlugin without TAS driver. Fix your configuration to continue")

    def get_credentials_list(self, provider, username):
        credentials_list = []
        tacc_username = self.tas_driver._xsede_to_tacc_username(username)
        if not tacc_username:
            logger.warn(
                "TAS Driver found no TACC Username for XUP User %s"
                % username)
            tacc_username = username
        tacc_projects = self.tas_driver.find_projects_for(tacc_username)
        for tacc_project in tacc_projects:
            tacc_projectname = tacc_project['chargeCode']
            tacc_leader_username = tacc_project.get('pi', {})\
                .get('username', '')
            is_leader = tacc_leader_username == tacc_username
            credentials_list.append({
                'account_user': username,
                'username': tacc_username,
                'project_name': tacc_projectname,
                'group_name': tacc_projectname,
                'is_leader': False,
            })
        return credentials_list
