"""The shared MongoDB database for data this service stores outside of casbin."""

import os

from pymongo import MongoClient

mongo_client = MongoClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017/"))

database = mongo_client[os.getenv("MONGODB_DB_NAME", "auth_service")]
