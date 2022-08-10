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
            passwordstate = passwords.PasswordstateLookup(
                os.getenv('PASSWORD_API_BASE_URL'),
                os.getenv('PASSWORD_API_KEY'))
            password_data = passwordstate.get_pw_by_title(
                os.getenv('PASSWORD_API_LIST_ID'),
                os.getenv('PASSWORD_TITLE'))
            mongo_connection = os.getenv('MONGODB_URL')
            client = MongoClient(mongo_connection.replace(
                'password', password_data))
            cls.account_collection = client['Accounts'].get_collection(
                'accounts')

    @classmethod
    def get_account_by_email(cls, email: str) -> dict:
        """
        Finds an account from the mongo database given an email addres.

        :param email: The email address of the account.
        """
        cls.__setup_database()

        account_data: dict = cls.account_collection.find_one({'email': email})
        if account_data is not None:
            account_data.pop('_id')
        return account_data
    
    @classmethod
    def get_account_by_authorization(cls, key: str, value: str) -> list[dict]:
        """
        Finds an account from the mongo database given an email addres.

        :param email: The email address of the account.
        """
        cls.__setup_database()

        account_data: list[dict] = cls.account_collection.find({key: value})
        return account_data

    @classmethod
    def update_account(cls, account: dict):
        """Updates an account in the database."""
        cls.__setup_database()
        return cls.account_collection.update_one({
            'email': account['email']},
            {'$set': account})


    @classmethod
    def delete_account(cls, account: dict):
        """
        Deletes an account from the mongo database.

        :param account: The account data.
        """
        cls.__setup_database()
        return cls.account_collection.delete_one({'email': account['email']})

    @classmethod
    def create_account(cls, account_data: dict):
        """
        Creates an account in the mongo database.

        :param account: The account data.
        """
        cls.__setup_database()
        return cls.account_collection.insert_one(account_data)
