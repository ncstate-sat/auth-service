import os
from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient(os.getenv('MONGODB_URL'))
account_collection = client['Accounts'].get_collection('accounts')


def get_account_by_id(account_id):
    account: dict = account_collection.find_one({'_id': ObjectId(account_id)})
    account['id'] = str(account['_id'])
    account.pop('_id')
    return account


def get_account_by_email(email):
    account: dict = account_collection.find_one({'email': email})
    account['id'] = str(account['_id'])
    account.pop('_id')
    return account


def get_account_by_campus_id(campus_id):
    account: dict = account_collection.find_one({'campus_id': campus_id})
    account['id'] = str(account['_id'])
    account.pop('_id')
    return account


def update_account_by_id(account_id, updated_record):
    updated_account = {'_id': ObjectId(account_id)}
    updated_account.update(updated_record)
    updated_account.pop('id')
    return account_collection.update_one({'_id': ObjectId(account_id)}, {'$set': updated_account})


def delete_account_by_id(account_id):
    return account_collection.delete_one({'_id': ObjectId(account_id)})


def create_account(email, campus_id, authorizations):
    new_account = {'email': email, 'campus_id': campus_id,
                   'authorizations': authorizations}
    insert_record = account_collection.insert_one(
        {'email': email, 'campus_id': campus_id, 'authorizations': authorizations})
    new_account.update({'id': str(insert_record.inserted_id)})
    return new_account
