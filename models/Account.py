"""A model to handle account CRUD."""


class Account:
    """The Account model handles CRUD functions for accounts."""
    email = None        # The email address of the account holder.
    roles = []          # The top-level roles assigned to the user.
    permissions = []    # The flattened list of granular permissions derived from the roles.

    def __init__(self, config):
        if 'email' in config:
            self.email = config['email']
        if 'roles' in config:
            self.roles = list(set(config['roles']))
        if 'permissions' in config:
            self.permissions = list(set(config['permissions']))

    def update(self):
        """Updates this instance in the database."""
        

    def add_role(self, role):
        """Adds a role to this user if it is not already added."""
        

    def remove_role(self, role):
        """Removes a role from this user, if they have it."""
        

    def delete(self):
        """Deletes this instance from the database."""
        

    @staticmethod
    def find_by_email(email):
        """
        Finds an account given an email address.

        Parameters:
            email: The email address of the account.
        """
        

    @staticmethod
    def find_by_role(role):
        """
        Finds accounts given authorization data.

        :param filter: The attribute that should be searched.
        """
        

    @staticmethod
    def create_account(email, roles=None):
        """
        Creates a new account in the database.

        :param email: The email address of the account.
        :param authorizations: The authorization data of the account.
        """
        
