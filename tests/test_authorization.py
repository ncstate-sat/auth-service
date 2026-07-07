"""Tests for the authorization controller functions."""

import os
from fastapi.testclient import TestClient
from main import app
from models.Token import Token
import util.enforcer
from util.enforcer import enforcer

client = TestClient(app)

ADMIN_ACCOUNT = {
    'email': 'admin@university.edu',
    'roles': ['admin'],
    'permissions': ['admin:read', 'admin:write', 'member:read', 'member:write']
}

MEMBER_ACCOUNT = {
    'email': 'member@university.edu',
    'roles': ['member'],
    'permissions': []
}

os.environ["JWT_SECRET"] = "TEST_SECRET"
EXPIRED_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2Njg3MDU2NzMsImVtYWlsIj"
    "oibG1lbmFAbmNzdS5lZHUiLCJjYW1wdXNfaWQiOiIwMDExMzI4MDgiLCJyb2xlcyI6WyJ0Z"
    "XN0X3VzZXIiXSwiYXV0aG9yaXphdGlvbnMiOnsiYXV0aDEiOnRydWUsImF1dGgyIjp0cnVl"
    "LCJhdXRoMyI6ZmFsc2UsIl9yZWFkIjpbXSwiX3dyaXRlIjpbXX19.UmLWB6Pf-hwQaHBdrg"
    "Iq662_H1ZwAT1fWBzL1sfApIo"
)
INVALID_SIGNATURE_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjQwOTk3Mzc4MDAsImVtYWlsIj"
    "oibG1lbmFAbmNzdS5lZHUiLCJjYW1wdXNfaWQiOiIwMDExMzI4MDgiLCJyb2xlcyI6WyJ0Z"
    "XN0X3VzZXIiXSwiYXV0aG9yaXphdGlvbnMiOnsiYXV0aDEiOnRydWUsImF1dGgyIjp0cnVl"
    "LCJhdXRoMyI6ZmFsc2UsInJvb3QiOnRydWUsIl9yZWFkIjpbXSwiX3dyaXRlIjpbXX19.qo"
    "4DfBZaP-rHptkcwNqh4Lcmhn14ClJ4NK1sKC499pY"
)


def mock_enforce_by_role(allowed_roles):
    """Builds a mock enforce() that allows any act on the given roles."""
    def _enforce(_sub, obj, _act):
        return obj in allowed_roles
    return _enforce


def test_get_accounts_with_role(monkeypatch):
    """
    It should get all users with a role.
    """
    def mock_get_roles_for_user(email):
        return ADMIN_ACCOUNT['roles'] if email == ADMIN_ACCOUNT['email'] else MEMBER_ACCOUNT['roles']

    def mock_get_implicit_permissions_for_user(email):
        return [] if email != ADMIN_ACCOUNT['email'] else [
            ['admin', obj, act] for perm in ADMIN_ACCOUNT['permissions']
            for obj, act in [perm.split(':')]
        ]

    def mock_get_users_for_role(role):
        return [MEMBER_ACCOUNT['email']] if role == 'member' else []

    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role(['member']))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', mock_get_roles_for_user)
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', mock_get_implicit_permissions_for_user)
    monkeypatch.setattr(enforcer, 'get_users_for_role', mock_get_users_for_role)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.get(
        '/role-accounts?role=member',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == 200
    assert response.json() == {
        'accounts': [{
            'email': MEMBER_ACCOUNT['email'],
            'roles': MEMBER_ACCOUNT['roles'],
            'permissions': []
        }]
    }

    expired_response = client.get(
        '/role-accounts?role=member',
        headers={'Authorization': f'Bearer {EXPIRED_JWT}'}
    )
    assert expired_response.status_code == 401
    assert 'accounts' not in expired_response.json()

    invalid_response = client.get(
                '/role-accounts?role=member',
        headers={'Authorization': f'Bearer {INVALID_SIGNATURE_JWT}'}
    )
    assert invalid_response.status_code == 400
    assert 'accounts' not in invalid_response.json()


def test_get_account_with_role_unauthorized(monkeypatch):
    """
    It should fail to get users with a certain role if the requesting account does not have authorization.
    """
    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role(['member']))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', lambda email: MEMBER_ACCOUNT['roles'])
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.get(
        '/role-accounts?role=admin',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == 400
    assert response.json() == {
        'error': 'This account is not authorized to read admin authorizations.'
    }


def test_add_role(monkeypatch):
    """
    It should be able to add a role to an account.
    """
    granted_roles = []

    def mock_get_roles_for_user(email):
        if email == MEMBER_ACCOUNT['email']:
            return MEMBER_ACCOUNT['roles'] + granted_roles
        return ADMIN_ACCOUNT['roles']

    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role(['admin', 'member']))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', mock_get_roles_for_user)
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])
    monkeypatch.setattr(enforcer, 'add_grouping_policy', lambda *_: granted_roles.append('admin'))
    monkeypatch.setattr(enforcer, 'remove_grouping_policy', lambda *_: None)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': MEMBER_ACCOUNT['email'],
            'add_roles': ['admin']
        }
    )

    assert response.status_code == 200
    assert response.json() == {
        'account': {
            'email': MEMBER_ACCOUNT['email'],
            'roles': ['member', 'admin']
        }
    }

    expired_response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {EXPIRED_JWT}'},
        json={
            'email': MEMBER_ACCOUNT['email'],
            'add_roles': ['admin']
        }
    )
    assert expired_response.status_code == 401
    assert 'account' not in expired_response.json()

    invalid_response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {INVALID_SIGNATURE_JWT}'},
        json={
            'email': MEMBER_ACCOUNT['email'],
            'add_roles': ['admin']
        }
    )
    assert invalid_response.status_code == 400
    assert 'account' not in invalid_response.json()


def test_add_role_unauthorized(monkeypatch):
    """
    It should fail to add roles to an account if the requesting account does not have authorization.
    """
    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role([]))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', lambda email: MEMBER_ACCOUNT['roles'])
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': ADMIN_ACCOUNT['email'],
            'add_roles': ['member']
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        'error': 'This account is not authorized to write to this user\'s authorization(s).'
    }


def test_remove_role(monkeypatch):
    """
    It should be able to remove multiple roles from an account.
    """
    remaining_roles = ['member']

    def mock_get_roles_for_user(email):
        if email == MEMBER_ACCOUNT['email']:
            return remaining_roles
        return ADMIN_ACCOUNT['roles']

    def mock_remove_grouping_policy(_email, role):
        remaining_roles.remove(role)

    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role(['admin', 'member']))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', mock_get_roles_for_user)
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])
    monkeypatch.setattr(enforcer, 'add_grouping_policy', lambda *_: None)
    monkeypatch.setattr(enforcer, 'remove_grouping_policy', mock_remove_grouping_policy)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': MEMBER_ACCOUNT['email'],
            'remove_roles': ['member']
        }
    )

    assert response.status_code == 200
    assert response.json() == {
        'account': {
            'email': MEMBER_ACCOUNT['email'],
            'roles': []
        }
    }


def test_remove_role_unauthorized(monkeypatch):
    """
    It should fail to remove roles if the requesting account does not have permission.
    """
    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role([]))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', lambda email: MEMBER_ACCOUNT['roles'])
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': ADMIN_ACCOUNT['email'],
            'remove_roles': ['admin']
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        'error': 'This account is not authorized to write to this user\'s authorization(s).'
    }


def test_add_and_remove_roles(monkeypatch):
    """
    It should be able to add and remove roles for an account.
    """
    account_roles = ['member']

    def mock_get_roles_for_user(email):
        if email == MEMBER_ACCOUNT['email']:
            return account_roles
        return ADMIN_ACCOUNT['roles']

    def mock_add_grouping_policy(_email, role):
        account_roles.append(role)

    def mock_remove_grouping_policy(_email, role):
        account_roles.remove(role)

    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role(['admin', 'member']))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', mock_get_roles_for_user)
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])
    monkeypatch.setattr(enforcer, 'add_grouping_policy', mock_add_grouping_policy)
    monkeypatch.setattr(enforcer, 'remove_grouping_policy', mock_remove_grouping_policy)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': MEMBER_ACCOUNT['email'],
            'add_roles': ['admin'],
            'remove_roles': ['member']
        }
    )

    assert response.status_code == 200
    assert response.json() == {
        'account': {
            'email': MEMBER_ACCOUNT['email'],
            'roles': ['admin']
        }
    }


def test_add_and_remove_roles_unauthorized(monkeypatch):
    """
    It should be able to add and remove roles for an account.
    """
    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role([]))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', lambda email: MEMBER_ACCOUNT['roles'])
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': ADMIN_ACCOUNT['email'],
            'add_roles': ['member'],
            'remove_roles': ['admin']
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        'error': 'This account is not authorized to write to this user\'s authorization(s).'
    }


def test_get_role_permissions(monkeypatch):
    """
    It should get the permissions granted to a role.
    """
    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role(['member']))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', lambda email: ADMIN_ACCOUNT['roles'])
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])
    monkeypatch.setattr(enforcer, 'get_filtered_policy', lambda _index, role: [[role, 'can_do_x', 'read']])

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.get(
        '/role-permissions?role=member',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == 200
    assert response.json() == {
        'permissions': [{'obj': 'can_do_x', 'act': 'read'}]
    }


def test_get_role_permissions_unauthorized(monkeypatch):
    """
    It should fail to get a role's permissions without read access to that role.
    """
    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role([]))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', lambda email: MEMBER_ACCOUNT['roles'])
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.get(
        '/role-permissions?role=admin',
        headers={'Authorization': f'Bearer {token}'}
    )

    assert response.status_code == 400
    assert response.json() == {
        'error': 'This account is not authorized to read admin authorizations.'
    }


def test_update_role_permissions(monkeypatch):
    """
    It should be able to add and remove permissions granted to a role.
    """
    role_policies = [['member', 'can_do_x', 'read']]

    def mock_add_policy(role, obj, act):
        role_policies.append([role, obj, act])

    def mock_remove_policy(role, obj, act):
        role_policies.remove([role, obj, act])

    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role(['admin', 'member']))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', lambda email: ADMIN_ACCOUNT['roles'])
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])
    monkeypatch.setattr(enforcer, 'add_policy', mock_add_policy)
    monkeypatch.setattr(enforcer, 'remove_policy', mock_remove_policy)
    monkeypatch.setattr(enforcer, 'get_filtered_policy',
                        lambda _index, role: [p for p in role_policies if p[0] == role])

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.put(
        '/update-role-permissions',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'role': 'member',
            'add_permissions': [{'obj': 'can_do_y', 'act': 'write'}],
            'remove_permissions': [{'obj': 'can_do_x', 'act': 'read'}]
        }
    )

    assert response.status_code == 200
    assert response.json() == {
        'permissions': [{'obj': 'can_do_y', 'act': 'write'}]
    }


def test_update_role_permissions_unauthorized(monkeypatch):
    """
    It should fail to update a role's permissions without write access to that role.
    """
    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role([]))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', lambda email: MEMBER_ACCOUNT['roles'])
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.put(
        '/update-role-permissions',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'role': 'admin',
            'add_permissions': [{'obj': 'root', 'act': 'write'}]
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        'error': 'This account is not authorized to write to the admin role\'s permissions.'
    }


def test_root_admin_email_bypasses_authorization(monkeypatch):
    """
    ROOT_ADMIN_EMAIL should be authorized even when casbin would otherwise deny,
    so the first role/permissions can be bootstrapped on a fresh system.
    """
    root_email = 'root@university.edu'
    monkeypatch.setattr(util.enforcer, 'ROOT_ADMIN_EMAIL', root_email)
    monkeypatch.setattr(enforcer, 'enforce', mock_enforce_by_role([]))
    monkeypatch.setattr(enforcer, 'get_roles_for_user', lambda email: [])
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user', lambda email: [])
    monkeypatch.setattr(enforcer, 'add_policy', lambda *_: None)
    monkeypatch.setattr(enforcer, 'get_filtered_policy', lambda *_: [])

    token = Token.generate_token({'email': root_email, 'roles': [], 'permissions': []})
    response = client.put(
        '/update-role-permissions',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'role': 'admin',
            'add_permissions': [{'obj': 'admin', 'act': 'write'}]
        }
    )

    assert response.status_code == 200
    assert response.json() == {
        'permissions': []
    }
