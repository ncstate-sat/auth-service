"""Tests for the role management controller functions."""

import os
from fastapi.testclient import TestClient
from main import app
from models.Token import Token
from util import casbin_enforcer
from util.casbin_enforcer import build_test_enforcer

client = TestClient(app)

os.environ["JWT_SECRET"] = "TEST_SECRET"

ADMIN_ROLE = {
    'name': 'admin',
    'authorizations': {
        'root': True,
        '_read': ['member'],
        '_write': ['member']
    }
}

MEMBER_ROLE = {
    'name': 'member',
    'authorizations': {
        '_read': [],
        '_write': []
    }
}

ALL_ROLES = [ADMIN_ROLE, MEMBER_ROLE]

ADMIN_ACCOUNT = {'email': 'admin@university.edu', 'roles': ['admin']}
MEMBER_ACCOUNT = {'email': 'member@university.edu', 'roles': ['member']}

ALL_USER_ROLES = [
    ('admin@university.edu', 'admin'),
    ('member@university.edu', 'member'),
]


def test_list_roles(monkeypatch):
    """Root users can list all roles."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.get('/roles', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    roles = {r['name']: r for r in response.json()['roles']}
    assert 'admin' in roles
    assert 'member' in roles
    assert roles['admin'].get('root') is True
    assert roles['admin']['read'] == ['member']
    assert roles['admin']['write'] == ['member']
    assert roles['member']['read'] == []
    assert roles['member']['write'] == []


def test_list_roles_unauthorized(monkeypatch):
    """Non-root users cannot list roles."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.get('/roles', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400
    assert 'roles' not in response.json()


def test_create_role(monkeypatch):
    """Root users can create a new role."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.post(
        '/roles',
        headers={'Authorization': f'Bearer {token}'},
        json={'name': 'editor', 'read': ['member'], 'write': [], 'root': False}
    )

    assert response.status_code == 200
    assert response.json()['role']['name'] == 'editor'
    assert response.json()['role']['read'] == ['member']
    assert response.json()['role']['write'] == []
    assert 'root' not in response.json()['role']


def test_create_role_conflict(monkeypatch):
    """Creating a role that already exists returns 409."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.post(
        '/roles',
        headers={'Authorization': f'Bearer {token}'},
        json={'name': 'member', 'read': [], 'write': [], 'root': False}
    )

    assert response.status_code == 409


def test_create_role_unauthorized(monkeypatch):
    """Non-root users cannot create roles."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.post(
        '/roles',
        headers={'Authorization': f'Bearer {token}'},
        json={'name': 'editor', 'read': [], 'write': [], 'root': False}
    )

    assert response.status_code == 400


def test_get_role(monkeypatch):
    """Root users can retrieve a single role."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.get('/roles/member', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    assert response.json()['role']['name'] == 'member'


def test_get_role_not_found(monkeypatch):
    """Returns 404 for an unknown role."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.get('/roles/nonexistent', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 404


def test_update_role(monkeypatch):
    """Root users can replace a role's permissions."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.put(
        '/roles/member',
        headers={'Authorization': f'Bearer {token}'},
        json={'read': ['admin'], 'write': [], 'root': False}
    )

    assert response.status_code == 200
    assert response.json()['role']['read'] == ['admin']
    assert response.json()['role']['write'] == []


def test_update_role_unauthorized(monkeypatch):
    """Non-root users cannot update roles."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.put(
        '/roles/member',
        headers={'Authorization': f'Bearer {token}'},
        json={'read': ['admin'], 'write': [], 'root': False}
    )

    assert response.status_code == 400


def test_delete_role(monkeypatch):
    """Root users can delete a role; users are unassigned from it."""
    enforcer = build_test_enforcer(ALL_ROLES, ALL_USER_ROLES)
    monkeypatch.setattr(casbin_enforcer, '_enforcer', enforcer)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.delete('/roles/member', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    assert response.json()['deleted'] == 'member'

    # The role should no longer appear in the enforcer policies.
    assert enforcer.get_filtered_policy(0, 'member') == []
    # The member user should no longer have the member role grouping.
    assert 'member' not in enforcer.get_roles_for_user('member@university.edu')


def test_delete_role_not_found(monkeypatch):
    """Returns 404 when deleting a non-existent role."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.delete('/roles/nonexistent', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 404


def test_delete_role_unauthorized(monkeypatch):
    """Non-root users cannot delete roles."""
    monkeypatch.setattr(casbin_enforcer, '_enforcer', build_test_enforcer(ALL_ROLES, ALL_USER_ROLES))

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.delete('/roles/admin', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400
