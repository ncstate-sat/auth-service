"""A model to handle account CRUD."""

import util.db as db


class Account:
    """The Account model handles CRUD functions for accounts."""
    email = None
    campus_id = None
    authorizations = {}

    def __init__(self, config):
        if 'email' in config:
            self.email = config['email']
        if 'campus_id' in config:
            self.campus_id = config['campus_id']
        if 'authorizations' in config:
            self.authorizations = config['authorizations']

    def update(self):
        """Updates this instance in the database."""
        return db.update_account(self.__dict__)

    def delete(self):
        """Deletes this instance from the database."""
        return db.delete_account(self.__dict__)

    def get_authorization(self, service_name):
        """Returns the authorization data given a service name. Does not """
        return self.authorizations[service_name]

    def update_authorization(self, service_name, auth_info):
        """Updates an authorization record given a service name."""
        self.authorizations[service_name] = auth_info
        return

    def remove_authorization(self, service_name):
        """Removes an authorization record given a service name."""
        if service_name in self.authorizations:
            return self.authorizations.pop(service_name)
        else:
            raise RuntimeError('This service does not exist in this authorization.')

    @staticmethod
    def find_by_email(email):
        """
        Finds an account given an email address.

        :param email: The email addres of the account.
        """
        db_account = db.get_account_by_email(email)
        if db_account is None:
            new_account = Account.create_account(email, None)
            return new_account
        else:
            return Account(config=db_account)

    @staticmethod
    def find_by_authorization(app_id, db_filter, value):
        """
        Finds accounts given authorization data.

        :param filter: The attribute that should be searched.
        """
        db_accounts = db.get_account_by_authorization(f'authorizations.{app_id}.{db_filter}', value)
        accounts = []
        for account in db_accounts:
            accounts.append(Account(config=account))

        return accounts


    @staticmethod
    def create_account(email, campus_id, authorizations=None):
        """
        Creates a new account in the database.

        :param email: The email address of the account.
        :param campus_id: The campus ID of the new account.
        :param authorizations: The authorization data of the account.
        """
        if authorizations is None:
            authorizations = {}
        account_data = {'email': email, 'campus_id': campus_id,
                        'authorizations': authorizations}
        db.create_account(account_data)
        return Account(config=account_data)
