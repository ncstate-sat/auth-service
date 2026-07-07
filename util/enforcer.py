import casbin
import casbin_pymongo_adapter

adapter = casbin_pymongo_adapter.Adapter('mongodb://localhost:27017/', "auth_service")

enforcer = casbin.Enforcer('/util/model.conf', adapter, True)