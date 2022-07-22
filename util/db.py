"""
CRUD functions for the database.
"""

import os
from pymongo import MongoClient
import passwords


class AuthDB:
    """Helper class for database functions."""
    account_collection = None

    @classmethod
    def __setup_database(cls):
        """Gets password from Passwordstate."""
        if cls.account_collection is None:
            passwordstate = passwords.PasswordstateLookup(os.getenv('API_KEY'))
            password_data = passwordstate.get_pw(os.getenv('MONGO_PASSWORD_ID'))
            mongo_connection = os.getenv('MONGODB_URL')
            client = MongoClient(mongo_connection.replace('password', password_data))
            cls.account_collection = client['Accounts'].get_collection('accounts')

    @classmethod
    def get_account_by_email(cls, email: str) -> dict:
        """Finds an account by email address."""
        cls.__setup_database()

        account_data: dict = cls.account_collection.find_one({'email': email})
        if account_data is not None:
            account_data.pop('_id')
        return account_data

    @classmethod
    def update_account(cls, account: dict):
        """Updates an account in the database."""
        cls.__setup_database()

        return cls.account_collection.update_one({'email': account['email']}, {'$set': account})

    @classmethod
    def delete_account(cls, account: dict):
        """Deletes an account from the database."""
        cls.__setup_database()

        return cls.account_collection.delete_one({'email': account['email']})

    @classmethod
    def create_account(cls, account_data: dict):
        """Creates a new account in the database."""
        cls.__setup_database()

        return cls.account_collection.insert_one(account_data)
