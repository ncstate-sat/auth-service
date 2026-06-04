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
            The account document (email only — roles and authorizations are owned by Casbin).
        """
        cls.__setup_database()

        account_data = cls.account_collection.find_one({'email': email})
        if account_data is not None:
            account_data.pop('_id')
            account_data.pop('roles', None)  # Roles are authoritative in Casbin, not MongoDB.

        return account_data

    @classmethod
    def update_account(cls, account: dict):
        """
        Updates an account in the database.

        Parameters:
            account: The account data.
        """
        cls.__setup_database()

        account_copy = account.copy()
        account_copy.pop('authorizations', None)
        account_copy.pop('roles', None)  # Roles are owned by Casbin.

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
    def get_all_roles(cls) -> list[dict]:
        """Gets all roles from the database."""
        cls.__setup_database()
        return list(cls.role_collection.find({}, {'_id': 0}))

    @classmethod
    def get_all_accounts(cls) -> list[dict]:
        """Gets all accounts. Used during one-time Casbin policy migration."""
        cls.__setup_database()
        return list(cls.account_collection.find({}, {'_id': 0}))

    @classmethod
    def create_account(cls, account_data: dict):
        """
        Creates an account in the mongo database.

        Parameters
            account_data: The account data.
        """
        cls.__setup_database()
        return cls.account_collection.insert_one(account_data)
