"""Functions for the models to easily interface with the database."""

import os
from pymongo import MongoClient

client = MongoClient(os.getenv('MONGODB_URL'))
account_collection = client['Accounts'].get_collection('accounts')


def get_account_by_email(email) -> dict:
    """
    Finds an account from the mongo database given an email addres.

    :param email: The email address of the account.
    """
    account_data: dict = account_collection.find_one({'email': email})
    if account_data is not None:
        account_data.pop('_id')
    return account_data


def get_account_by_authorization(filter_string, value) -> list[dict]:
    """
    Finds all accounts given a deep query into authorizations.

    :params filter_string: The attribute deep the the document which should be queried.
    :params value: The value the filter string should be.
    """
    print(filter_string)
    print(value)
    return account_collection.find({filter_string: value})


def update_account(account: dict):
    """
    Updates an account in the mongo database.

    :param account: The account data.
    """
    return account_collection.update_one({'email': account['email']}, {'$set': account})


def delete_account(account: dict):
    """
    Deletes an account from the mongo database.

    :param account: The account data.
    """
    return account_collection.delete_one({'email': account['email']})


def create_account(account_data):
    """
    Creates an account in the mongo database.

    :param account: The account data.
    """
    return account_collection.insert_one(account_data)
