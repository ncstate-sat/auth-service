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
    seen = set()
    for email, role_name in (user_roles or []):
        enforcer.add_role_for_user(email, role_name)
        if email not in seen:
            enforcer.add_role_for_user(email, '_user')
            seen.add(email)
    return enforcer


def build_authorizations(enforcer: casbin.Enforcer, roles: list) -> dict:
    """
    Builds the authorizations dict embedded in JWT payloads.

    All data is derived from Casbin policies — no MongoDB lookups.
    root is True when any of the user's roles has a wildcard write policy.
    """
    _read = set()
    _write = set()
    is_root = False

    for role in roles:
        for _, obj, act in enforcer.get_filtered_policy(0, role):
            if obj == '*':
                is_root = True
            else:
                if act == 'read':
                    _read.add(obj)
                elif act == 'write':
                    _write.add(obj)

    authorizations = {
        '_read': sorted(_read),
        '_write': sorted(_write),
    }
    if is_root:
        authorizations['root'] = True
    return authorizations


