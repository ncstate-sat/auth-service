"""A model to handle account CRUD."""

from util.casbin_enforcer import get_enforcer, build_authorizations

SENTINEL = '_user'


class Account:
    """The Account model handles CRUD functions for accounts."""
    email = None
    roles = []
    authorizations = {}

    def __init__(self, config):
        if 'email' in config:
            self.email = config['email']
        if 'roles' in config:
            self.roles = list(set(config['roles']))
        if 'authorizations' in config:
            self.authorizations = config['authorizations']

    def add_role(self, role):
        """Adds a role to this user if not already present. Persists to Casbin immediately."""
        if role not in self.roles:
            self.roles.append(role)
            get_enforcer().add_role_for_user(self.email, role)

    def remove_role(self, role):
        """Removes a role from this user if present. Persists to Casbin immediately."""
        if role in self.roles:
            self.roles.remove(role)
            get_enforcer().delete_role_for_user(self.email, role)

    def delete(self):
        """Removes this account and all its role assignments from Casbin."""
        get_enforcer().delete_roles_for_user(self.email)

    @staticmethod
    def find_by_email(email):
        """
        Finds an account given an email address. Auto-creates it on first sign-in.

        Parameters:
            email: The email address of the account.
        """
        enforcer = get_enforcer()
        all_groupings = enforcer.get_roles_for_user(email)

        if SENTINEL not in all_groupings:
            return Account.create_account(email)

        roles = [r for r in all_groupings if r != SENTINEL]
        authorizations = build_authorizations(enforcer, roles)
        return Account(config={'email': email, 'roles': roles, 'authorizations': authorizations})

    @staticmethod
    def find_by_role(role):
        """
        Finds all accounts that have a given role.

        :param role: The role name to search by.
        """
        enforcer = get_enforcer()
        emails = enforcer.get_users_for_role(role)
        return [Account.find_by_email(email) for email in emails]

    @staticmethod
    def create_account(email, roles=None):
        """
        Creates a new account, recording its existence in Casbin.

        :param email: The email address of the account.
        :param roles: Optional list of roles to assign immediately.
        """
        enforcer = get_enforcer()
        enforcer.add_role_for_user(email, SENTINEL)
        account = Account(config={
            'email': email,
            'roles': [],
            'authorizations': {'_read': [], '_write': []}
        })
        for role in (roles or []):
            account.add_role(role)
        return account
