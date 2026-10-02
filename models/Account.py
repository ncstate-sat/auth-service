"""A model to handle account CRUD."""

import re

from util.enforcer import enforcer

EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class Account:
    """The Account model handles CRUD functions for accounts."""
    email = None           # The email address of the account holder.
    roles = []             # The top-level roles assigned to the user.
    inherited_roles = []   # Roles inherited transitively through the user's assigned roles.
    permissions = []       # The flattened list of granular permissions derived from the roles.

    def __init__(self, config):
        if 'email' in config:
            self.email = config['email']
        if 'roles' in config:
            self.roles = list(set(config['roles']))
        if 'inherited_roles' in config:
            self.inherited_roles = list(set(config['inherited_roles']))
        if 'permissions' in config:
            self.permissions = list(set(config['permissions']))

    def add_role(self, role):
        """Adds a role to this user if it is not already added."""
        if role not in self.roles:
            enforcer.add_grouping_policy(self.email, role)
            self.roles.append(role)
            self.inherited_roles = Account._flatten_inherited_roles(self.email, self.roles)
            self.permissions = Account._flatten_permissions(self.email)

    def remove_role(self, role):
        """Removes a role from this user, if they have it."""
        if role in self.roles:
            enforcer.remove_grouping_policy(self.email, role)
            self.roles.remove(role)
            self.inherited_roles = Account._flatten_inherited_roles(self.email, self.roles)
            self.permissions = Account._flatten_permissions(self.email)

    def delete(self):
        """Deletes this instance from the database."""
        return enforcer.remove_filtered_grouping_policy(0, self.email)

    @staticmethod
    def find_by_email(email):
        """
        Finds an account given an email address.

        Parameters:
            email: The email address of the account.
        """
        roles = enforcer.get_roles_for_user(email)
        return Account({
            'email': email,
            'roles': roles,
            'inherited_roles': Account._flatten_inherited_roles(email, roles),
            'permissions': Account._flatten_permissions(email)
        })

    @staticmethod
    def find_by_role(role):
        """
        Finds accounts given authorization data.

        :param filter: The attribute that should be searched.
        """
        # get_users_for_role returns every node with a direct grouping-policy edge into
        # this role, which includes other roles that inherit from it (not just accounts),
        # since accounts and roles share the same casbin grouping relation.
        return [
            Account.find_by_email(email)
            for email in enforcer.get_users_for_role(role)
            if EMAIL_PATTERN.match(email)
        ]

    @staticmethod
    def create_account(email, roles=None):
        """
        Creates a new account in the database.

        :param email: The email address of the account.
        :param roles: The roles to grant the account.
        """
        account = Account({'email': email, 'roles': []})
        for role in (roles or []):
            account.add_role(role)

        return account

    @staticmethod
    def _flatten_permissions(email):
        """Flattens this user's implicit (role, obj, act) permissions into 'obj:act' strings."""
        return list({
            f'{obj}:{act}'
            for _, obj, act in enforcer.get_implicit_permissions_for_user(email)
        })

    @staticmethod
    def _flatten_inherited_roles(email, roles=None):
        """Finds the roles this user's assigned roles inherit from, transitively.

        get_implicit_roles_for_user() returns the user's directly assigned roles plus
        every role reachable from them, so the directly assigned roles are subtracted
        out to leave only the ones gained through inheritance.
        """
        if roles is None:
            roles = enforcer.get_roles_for_user(email)
        return list(set(enforcer.get_implicit_roles_for_user(email)) - set(roles))
