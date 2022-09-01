"""A model to handle account CRUD."""

from util.db import AuthDB


class Account:
    """The Account model handles CRUD functions for accounts."""
    email = None
    campus_id = None
    roles = []
    authorizations = {}

    def __init__(self, config):
        if 'email' in config:
            self.email = config['email']
        if 'campus_id' in config:
            self.campus_id = config['campus_id']
        if 'roles' in config:
            self.roles = list(set(config['roles']))
        if 'authorizations' in config:
            self.authorizations = config['authorizations']

    def update(self):
        """Updates this instance in the database."""
        return AuthDB.update_account(self.__dict__)

    def add_role(self, role):
        """Adds a role to this user if it is not already added."""
        if role not in self.roles:
            self.roles.append(role)

    def remove_role(self, role):
        """Removes a role from this user, if they have it."""
        if role in self.roles:
            self.roles.remove(role)

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
            new_account = Account.create_account(email, None)
            return new_account
        else:
            return Account(config=db_account)

    @staticmethod
    def find_by_role(role):
        """
        Finds accounts given authorization data.

        :param filter: The attribute that should be searched.
        """
        db_accounts = AuthDB.get_account_by_role(role)

        accounts = []
        for account in db_accounts:
            accounts.append(Account(config=account))

        print(accounts)
        return accounts

    @staticmethod
    def create_account(email, campus_id, roles=None):
        """
        Creates a new account in the database.

        :param email: The email address of the account.
        :param campus_id: The campus ID of the new account.
        :param authorizations: The authorization data of the account.
        """
        if roles is None:
            roles = []
        account_data = {'email': email, 'campus_id': campus_id,
                        'roles': roles}
        AuthDB.create_account(account_data)
        return Account(config=account_data)
