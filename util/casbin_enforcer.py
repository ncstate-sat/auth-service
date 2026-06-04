import os
import casbin
from casbin.persist.adapter import Adapter

# The enforcer is Casbin's core object. It answers the question "can user X perform
# action Y on resource Z?" by consulting two tables:
#   - Policies: (role, resource, action) triples that grant permissions to roles.
#   - Role groupings: (user, role) pairs that say which roles a user belongs to.
# enforcer.enforce(user, resource, action) returns True if the user has at least one
# role whose policy permits that action on that resource (or on the wildcard '*').
#
# Policies and role groupings are persisted to a `casbin_rules` MongoDB collection
# via casbin_pymongo_adapter, making Casbin the authoritative store for all RBAC data.

_enforcer = None
_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'casbin_model.conf'))


class _EmptyAdapter(Adapter):
    # No-op in-memory adapter used in tests. Production uses casbin_pymongo_adapter,
    # which persists policies to the `casbin_rules` MongoDB collection automatically.
    def load_policy(self, model): pass
    def save_policy(self, model): pass
    def add_policy(self, sec, ptype, rule): pass
    def remove_policy(self, sec, ptype, rule): pass
    def remove_filtered_policy(self, sec, ptype, field_index, *field_values): pass


def _build_enforcer() -> casbin.Enforcer:
    from casbin_pymongo_adapter import Adapter as MongoAdapter
    adapter = MongoAdapter(os.environ['MONGODB_URL'], 'Accounts')
    return casbin.Enforcer(_MODEL_PATH, adapter)


def get_enforcer() -> casbin.Enforcer:
    # Lazy singleton: build the enforcer from the database on first call, then reuse it.
    global _enforcer
    if _enforcer is None:
        _enforcer = _build_enforcer()
    return _enforcer


def reset_enforcer():
    """Reset the cached enforcer so it reinitializes on next use. For testing."""
    global _enforcer
    _enforcer = None


def build_test_enforcer(roles: list, user_roles: list = None) -> casbin.Enforcer:
    """
    Creates an in-memory enforcer seeded with role policy data and optional user-role
    groupings. Used in tests in place of the MongoDB-backed production enforcer.

    roles: list of role dicts (same shape as MongoDB roles collection documents)
    user_roles: list of (email, role_name) tuples
    """
    enforcer = casbin.Enforcer(_MODEL_PATH, _EmptyAdapter())
    for role in roles:
        name = role['name']
        auths = role.get('authorizations', {})
        if auths.get('root'):
            enforcer.add_policy(name, '*', 'read')
            enforcer.add_policy(name, '*', 'write')
        for target in auths.get('_read', []):
            enforcer.add_policy(name, target, 'read')
        for target in auths.get('_write', []):
            enforcer.add_policy(name, target, 'write')
    for email, role_name in (user_roles or []):
        enforcer.add_role_for_user(email, role_name)
    return enforcer


def build_authorizations(enforcer: casbin.Enforcer, roles: list, all_roles_from_db: list) -> dict:
    """
    Builds the authorizations dict embedded in JWT payloads.

    _read and _write are derived from Casbin policies (Casbin is authoritative for RBAC).
    Custom domain flags (root, can_do_x, etc.) are read from MongoDB role documents,
    since they describe application capabilities rather than access-control rules.
    """
    authorizations = {}
    _read = set()
    _write = set()

    for role in roles:
        # get_filtered_policy(0, role) returns all policies where the first field equals role.
        for _, obj, act in enforcer.get_filtered_policy(0, role):
            if obj != '*':  # Wildcard is expressed as root flag, not a literal list entry.
                if act == 'read':
                    _read.add(obj)
                elif act == 'write':
                    _write.add(obj)

    # Merge custom domain flags from MongoDB roles, excluding _read/_write which Casbin owns.
    role_map = {r['name']: r for r in all_roles_from_db}
    for role in roles:
        role_auths = role_map.get(role, {}).get('authorizations', {})
        for key, value in role_auths.items():
            if key not in ('_read', '_write'):
                authorizations[key] = value

    authorizations['_read'] = sorted(_read)
    authorizations['_write'] = sorted(_write)
    return authorizations


def migrate_policies_from_mongodb(enforcer: casbin.Enforcer):
    """
    One-time migration: seeds Casbin with role policies and user-role groupings from
    the legacy MongoDB schema (_read/_write on roles, roles list on accounts).
    Skips silently if Casbin already has data, so it is safe to call on every startup.
    """
    if enforcer.get_policy() or enforcer.get_grouping_policy():
        return

    from util.db import AuthDB

    for role in AuthDB.get_all_roles():
        name = role['name']
        auths = role.get('authorizations', {})
        if auths.get('root'):
            enforcer.add_policy(name, '*', 'read')
            enforcer.add_policy(name, '*', 'write')
        for target in auths.get('_read', []):
            enforcer.add_policy(name, target, 'read')
        for target in auths.get('_write', []):
            enforcer.add_policy(name, target, 'write')

    for account in AuthDB.get_all_accounts():
        for role in account.get('roles', []):
            enforcer.add_role_for_user(account['email'], role)
