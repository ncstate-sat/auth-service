"""
CRUD functions for the database.
"""

import os
from pymongo import MongoClient


class AuthDB:
    """Helper class for database functions."""
    account_collection = None
    role_collection = None

    @classmethod
    def __setup_database(cls):
        """Gets 'accounts' and 'roles' collections from MongoDB."""
        if cls.account_collection is None or cls.role_collection is None:
            client = MongoClient(os.getenv('MONGODB_URL'))
            cls.account_collection = client['Accounts'].get_collection(
                'accounts')
            cls.role_collection = client['Accounts'].get_collection(
                'roles')

    @classmethod
    def get_account_by_email(cls, email: str) -> dict:
        """
        Finds an account from the mongo database given an email address.

        Parameters:
            email: The email address of the account.

        Returns:
            The account data.
        """
        cls.__setup_database()

        account_data: dict = cls.account_collection.find_one({'email': email})

        if account_data is not None:
            authorization_data: list[dict] = cls.role_collection.find(
                {'name': {'$in': account_data.get('roles', [])}})

            authorizations = {}
            read_roles = []
            write_roles = []
            for data in authorization_data:
                data_read_roles = data.get('authorizations', {}).get('_read', [])
                data_write_roles = data.get('authorizations', {}).get('_write', [])
                data['authorizations'].pop('_read')
                data['authorizations'].pop('_write')
                data.pop('_id')
                authorizations.update(data['authorizations'])
                read_roles = read_roles + data_read_roles
                write_roles = write_roles + data_write_roles

            account_data.pop('_id')
            authorizations['_read'] = read_roles
            authorizations['_write'] = write_roles
            account_data['authorizations'] = authorizations

        return account_data

    @classmethod
    def get_accounts_by_role(cls, value: str) -> list[dict]:
        """
        Finds all accounts from the mongo database that have a given
        authorization.

        Parameters:
            key: The key in the user's authorization data to test.
            value: The value which will be true for all returned accounts.

        Returns:
            All accounts with the given authorization.
        """
        cls.__setup_database()

        account_data: list[dict] = cls.account_collection.aggregate([
            {
                '$match': {'roles': value}
            },
            {
                '$lookup': {
                    'from': 'roles',
                    'localField': 'roles',
                    'foreignField': 'name',
                    'as': 'authorizations'
                }
            }
        ])

        transformed_account_data = []
        for data in account_data:
            authorizations = {}
            read_roles = []
            write_roles = []
            for auth in data['authorizations']:
                data_read_roles = auth.get('authorizations', {}).get('_read', [])
                data_write_roles = auth.get('authorizations', {}).get('_write', [])
                auth['authorizations'].pop('_read')
                auth['authorizations'].pop('_write')
                authorizations.update(auth.get('authorizations', {}))
                read_roles = read_roles + data_read_roles
                write_roles = write_roles + data_write_roles

            data.pop('_id')
            authorizations['_read'] = read_roles
            authorizations['_write'] = write_roles
            data['authorizations'] = authorizations
            transformed_account_data.append(data)

        return transformed_account_data

    @classmethod
    def update_account(cls, account: dict):
        """
        Updates an account in the database.

        Parameters:
            account: The account data.
        """
        cls.__setup_database()

        account_copy = account.copy()
        if account_copy.get('authorizations', False):
            account_copy.pop('authorizations')

        return cls.account_collection.update_one({
            'email': account_copy['email']},
            {'$set': account_copy})

    @classmethod
    def delete_account(cls, account: dict):
        """
        Deletes an account from the mongo database.

        Parameters:
            account: The account data.
        """
        cls.__setup_database()
        return cls.account_collection.delete_one({'email': account['email']})

    @classmethod
    def create_account(cls, account_data: dict):
        """
        Creates an account in the mongo database.

        Parameters
            account_data: The account data.
        """
        cls.__setup_database()
        return cls.account_collection.insert_one(account_data)
