import os
import casbin
import casbin_pymongo_adapter

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.conf')

adapter = casbin_pymongo_adapter.Adapter(
    os.getenv('MONGODB_URL', 'mongodb://localhost:27017/'), "auth_service"
)

enforcer = casbin.Enforcer(MODEL_PATH, adapter, True)


def is_authorized(sub, obj, act):
    """Checks casbin authorization, with a standing bypass for ROOT_ADMIN_EMAIL.

    ROOT_ADMIN_EMAIL exists to bootstrap the first role/permission on a fresh
    system, where no one yet has any casbin policy granting them access.
    """
    ROOT_ADMIN_EMAIL = os.getenv('ROOT_ADMIN_EMAIL')

    if ROOT_ADMIN_EMAIL and sub == ROOT_ADMIN_EMAIL:
        return True
    return enforcer.enforce(sub, obj, act)