import os
import casbin
import casbin_pymongo_adapter

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.conf')

adapter = casbin_pymongo_adapter.Adapter('mongodb://localhost:27017/', "auth_service")

enforcer = casbin.Enforcer(MODEL_PATH, adapter, True)