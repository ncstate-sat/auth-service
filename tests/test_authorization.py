"""Tests for the authorization controller functions."""

import os
from fastapi.testclient import TestClient
from main import app
from models.Token import Token
from util.db import AuthDB
from util import casbin_enforcer
from util.casbin_enforcer import build_test_enforcer

client = TestClient(app)

ADMIN_ROLE = {
    'name': 'admin',
    'authorizations': {
        'root': True,
        '_read': ['admin', 'member'],
        '_write': ['admin', 'member']
    }
}

MEMBER_ROLE = {
    'name': 'member',
    'authorizations': {
        'can_do_x': True,
        'can_do_y': True,
        '_read': [],
        '_write': []
    }
}

ALL_ROLES = [ADMIN_ROLE, MEMBER_ROLE]

ADMIN_ACCOUNT = {
    'email': 'admin@university.edu',
    'roles': ['admin']
}

MEMBER_ACCOUNT = {
    'email': 'member@university.edu',
    'roles': ['member']
}

# Both accounts pre-loaded into each test enforcer.
ALL_USER_ROLES = [
    ('admin@university.edu', 'admin'),
    ('member@university.edu', 'member'),
]

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


def test_get_accounts_with_role(monkeypatch):
    """
    It should get all users with a role.
    """
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))
    monkeypatch.setattr(AuthDB, 'get_account_by_email', lambda email: {'email': email})
    monkeypatch.setattr(AuthDB, 'get_all_roles', lambda: ALL_ROLES)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.get(
        '/role-accounts?role=member',
        headers={'Authorization': f'Bearer {token}'}
    )

    expected_accounts = {
        'email': 'member@university.edu',
        'roles': ['member'],
        'authorizations': {
            'can_do_x': True,
            'can_do_y': True,
            '_read': [],
            '_write': []
        }
    }

    assert response.status_code == 200
    assert response.json() == {
        'accounts': [expected_accounts]
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
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))
    monkeypatch.setattr(AuthDB, 'get_account_by_email', lambda email: {'email': email})
    monkeypatch.setattr(AuthDB, 'get_all_roles', lambda: ALL_ROLES)

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
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))
    monkeypatch.setattr(AuthDB, 'get_account_by_email', lambda email: {'email': email})
    monkeypatch.setattr(AuthDB, 'get_all_roles', lambda: ALL_ROLES)

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
            'email': 'member@university.edu',
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
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))
    monkeypatch.setattr(AuthDB, 'get_account_by_email', lambda email: {'email': email})
    monkeypatch.setattr(AuthDB, 'get_all_roles', lambda: ALL_ROLES)

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
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))
    monkeypatch.setattr(AuthDB, 'get_account_by_email', lambda email: {'email': email})
    monkeypatch.setattr(AuthDB, 'get_all_roles', lambda: ALL_ROLES)

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
            'email': 'member@university.edu',
            'roles': []
        }
    }


def test_remove_role_unauthorized(monkeypatch):
    """
    It should fail to remove roles if the requesting account does not have permission.
    """
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))
    monkeypatch.setattr(AuthDB, 'get_account_by_email', lambda email: {'email': email})
    monkeypatch.setattr(AuthDB, 'get_all_roles', lambda: ALL_ROLES)

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
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))
    monkeypatch.setattr(AuthDB, 'get_account_by_email', lambda email: {'email': email})
    monkeypatch.setattr(AuthDB, 'get_all_roles', lambda: ALL_ROLES)

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
            'email': 'member@university.edu',
            'roles': ['admin']
        }
    }


def test_add_and_remove_roles_unauthorized(monkeypatch):
    """
    It should fail to add and remove roles when the requesting account lacks permission.
    """
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))
    monkeypatch.setattr(AuthDB, 'get_account_by_email', lambda email: {'email': email})
    monkeypatch.setattr(AuthDB, 'get_all_roles', lambda: ALL_ROLES)

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
