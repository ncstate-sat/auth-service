import os
from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient(os.getenv('MONGODB_URL'))
account_collection = client['Accounts'].get_collection('accounts')


def get_account_by_email(email) -> dict:
    account_data: dict = account_collection.find_one({'email': email})
    if account_data is not None:
        account_data.pop('_id')
    return account_data


def update_account(account: dict):
    return account_collection.update_one({'email': account['email']}, {'$set': account})


def delete_account(account: dict):
    return account_collection.delete_one({'email': account['email']})


def create_account(account_data):
    return account_collection.insert_one(account_data)
