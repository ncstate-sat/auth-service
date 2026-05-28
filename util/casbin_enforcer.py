import os
import casbin
from casbin.persist.adapter import Adapter

_enforcer = None
_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'casbin_model.conf'))


class _EmptyAdapter(Adapter):
    """In-memory adapter with no initial policies."""
    def load_policy(self, model): pass
    def save_policy(self, model): pass
    def add_policy(self, sec, ptype, rule): pass
    def remove_policy(self, sec, ptype, rule): pass
    def remove_filtered_policy(self, sec, ptype, field_index, *field_values): pass


def _build_enforcer() -> casbin.Enforcer:
    from util.db import AuthDB
    enforcer = casbin.Enforcer(_MODEL_PATH, _EmptyAdapter())
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
    return enforcer


def get_enforcer() -> casbin.Enforcer:
    global _enforcer
    if _enforcer is None:
        _enforcer = _build_enforcer()
    return _enforcer


def reset_enforcer():
    """Reset the cached enforcer so it reinitializes on next use. For testing."""
    global _enforcer
    _enforcer = None


def sync_user_roles(enforcer: casbin.Enforcer, email: str, roles: list):
    """Register a user's current roles in the enforcer as grouping policies."""
    enforcer.delete_roles_for_user(email)
    for role in roles:
        enforcer.add_role_for_user(email, role)
