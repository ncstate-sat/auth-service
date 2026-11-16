import os
import casbin
import casbin_pymongo_adapter

MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.conf')

adapter = casbin_pymongo_adapter.Adapter(
    os.getenv("MONGODB_URL", "mongodb://localhost:27017/"),
    os.getenv("MONGODB_DB_NAME", "auth_service"),
)

enforcer = casbin.Enforcer(MODEL_PATH, adapter, True)


def is_authorized(sub, obj, act):
    """Checks casbin authorization, with a standing bypass for ROOT_ADMIN_EMAIL.

    ROOT_ADMIN_EMAIL exists to bootstrap the first role/permission on a fresh
    system, where no one yet has any casbin policy granting them access.
    """
    return is_root_admin(sub) or enforcer.enforce(sub, obj, act)


def is_root_admin(email):
    """Returns whether the email is the configured ROOT_ADMIN_EMAIL."""
    root_admin_email = os.getenv('ROOT_ADMIN_EMAIL')
    return bool(root_admin_email) and email == root_admin_email
