"""A model to handle account CRUD."""

from util.db import AuthDB
from util.casbin_enforcer import get_enforcer, build_authorizations


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

    def update(self):
        """Updates this instance in the database."""
        return AuthDB.update_account(self.__dict__)

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
        """Deletes this instance from the database."""
        return AuthDB.delete_account(self.__dict__)

    @staticmethod
    def find_by_email(email):
        """
        Finds an account given an email address.

        Parameters:
            email: The email address of the account.
        """
        db_account = AuthDB.get_account_by_email(email)
        if db_account is None:
            return Account.create_account(email)

        enforcer = get_enforcer()
        roles = enforcer.get_roles_for_user(email)
        all_roles = AuthDB.get_all_roles()
        authorizations = build_authorizations(enforcer, roles, all_roles)

        db_account['roles'] = roles
        db_account['authorizations'] = authorizations
        return Account(config=db_account)

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
        Creates a new account in the database.

        :param email: The email address of the account.
        :param roles: Optional list of roles to assign immediately.
        """
        AuthDB.create_account({'email': email})
        account = Account(config={
            'email': email,
            'roles': [],
            'authorizations': {'_read': [], '_write': []}
        })
        for role in (roles or []):
            account.add_role(role)
        return account
