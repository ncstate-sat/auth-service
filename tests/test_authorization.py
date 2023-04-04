"""Tests for the authorization controller functions."""

import os
from fastapi.testclient import TestClient
from main import app
from models.Token import Token
from util.db import AuthDB

client = TestClient(app)

ADMIN_ROLE = {
    'name': 'admin',
    'authorizations': {
        'root': True,
        '_read': ['admin, member'],
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

ADMIN_ACCOUNT = {
    'email': 'admin@university.edu',
    'roles': ['Admin']
}

MEMBER_ACCOUNT = {
    'email': 'member@university.edu',
    'roles': ['member']
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


def test_get_accounts_with_role(monkeypatch):
    """
    It should get all users with a role.
    """
    def mock_get_account_by_email(*_, **__):
        return {
            'email': 'admin@university.edu',
            'roles': ['admin'],
            'authorizations': {
                'root': True,
                '_read': ['admin', 'member'],
                '_write': ['admin', 'member']
            }
        }

    def mock_get_accounts_by_role(*_, **__):
        return [
            {
                'email': 'member@university.edu',
                'roles': ['member'],
                'authorizations': {
                    'can_do_x': True,
                    'can_do_y': True,
                    '_read': [],
                    '_write': []
                }
            }
        ]

    monkeypatch.setattr(AuthDB,
                        'get_account_by_email',
                        mock_get_account_by_email)

    monkeypatch.setattr(AuthDB,
                        'get_accounts_by_role',
                        mock_get_accounts_by_role)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.get(
        '/role-accounts?role=member',
        headers={'Authorization': f'Bearer {token}'}
    )

    expected_accounts = MEMBER_ACCOUNT.copy()
    expected_accounts.update({
        'authorizations': MEMBER_ROLE['authorizations']
    })

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
    def mock_get_account_by_email(*_, **__):
        return {
            'email': 'member@university.edu',
            'roles': ['member'],
            'authorizations': {
                'can_do_x': True,
                'can_do_y': True,
                '_read': [],
                '_write': []
            }
        }

    def mock_get_accounts_by_role(*_, **__):
        return [
            {
                'email': 'admin@university.edu',
                'roles': ['admin'],
                'authorizations': {
                    'root': True,
                    '_read': ['admin', 'member'],
                    '_write': ['admin', 'member']
                }
            }
        ]

    monkeypatch.setattr(AuthDB,
                        'get_account_by_email',
                        mock_get_account_by_email)

    monkeypatch.setattr(AuthDB,
                        'get_accounts_by_role',
                        mock_get_accounts_by_role)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.get(
        '/role-accounts?role=admin',
        headers={'Authorization': f'Bearer {token}'}
    )

    expected_accounts = MEMBER_ACCOUNT.copy()
    expected_accounts.update({
        'authorizations': MEMBER_ROLE['authorizations']
    })

    assert response.status_code == 400
    assert response.json() == {
        'error': 'This account is not authorized to read admin authorizations.'
    }


def test_add_role(monkeypatch):
    """
    It should be able to add a role to an account.
    """
    def mock_get_account_by_email(email):
        if email == 'member@university.edu':
            return {
                'email': 'member@university.edu',
                'roles': ['member'],
                'authorizations': {
                    'can_do_x': True,
                    'can_do_y': True,
                    '_read': [],
                    '_write': []
                }
            }
        else:
            return {
                'email': 'admin@university.edu',
                'roles': ['admin'],
                'authorizations': {
                    'root': True,
                    '_read': ['admin, member'],
                    '_write': ['admin', 'member']
                }
            }

    def mock_update_account(account_data):
        return account_data

    monkeypatch.setattr(AuthDB,
                        'get_account_by_email',
                        mock_get_account_by_email)

    monkeypatch.setattr(AuthDB,
                        'update_account',
                        mock_update_account)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': MEMBER_ACCOUNT['email'],
            'add_roles': ['admin']
        }
    )

    expected_account_state = MEMBER_ACCOUNT.copy()
    expected_account_state['roles'].append('admin')

    assert response.status_code == 200
    assert response.json() == {
        'account': expected_account_state
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
    def mock_get_account_by_email(email):
        if email == 'member@university.edu':
            return {
                'email': 'member@university.edu',
                'roles': ['member'],
                'authorizations': {
                    'can_do_x': True,
                    'can_do_y': True,
                    '_read': [],
                    '_write': []
                }
            }
        else:
            return {
                'email': 'admin@university.edu',
                'roles': ['admin'],
                'authorizations': {
                    'root': True,
                    '_read': ['admin, member'],
                    '_write': ['admin', 'member']
                }
            }

    def mock_update_account(account_data):
        return account_data

    monkeypatch.setattr(AuthDB,
                        'get_account_by_email',
                        mock_get_account_by_email)

    monkeypatch.setattr(AuthDB,
                        'update_account',
                        mock_update_account)

    token = Token.generate_token(MEMBER_ACCOUNT)
    response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': ADMIN_ACCOUNT['email'],
            'add_roles': ['member']
        }
    )

    expected_account_state = MEMBER_ACCOUNT.copy()
    expected_account_state['roles'].append('admin')

    assert response.status_code == 400
    assert response.json() == {
        'error': 'This account is not authorized to write to this user\'s authorization(s).'
    }


def test_remove_role(monkeypatch):
    """
    It should be able to remove multiple roles from an account.
    """
    def mock_get_account_by_email(email):
        if email == 'member@university.edu':
            return {
                'email': 'member@university.edu',
                'roles': ['member'],
                'authorizations': {
                    'can_do_x': True,
                    'can_do_y': True,
                    '_read': [],
                    '_write': []
                }
            }
        else:
            return {
                'email': 'admin@university.edu',
                'roles': ['admin'],
                'authorizations': {
                    'root': True,
                    '_read': ['admin, member'],
                    '_write': ['admin', 'member']
                }
            }

    def mock_update_account(account_data):
        return account_data

    monkeypatch.setattr(AuthDB,
                        'get_account_by_email',
                        mock_get_account_by_email)

    monkeypatch.setattr(AuthDB,
                        'update_account',
                        mock_update_account)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.put(
        '/update-account-roles',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': MEMBER_ACCOUNT['email'],
            'remove_roles': ['member']
        }
    )

    expected_account_state = {
        'email': 'member@university.edu',
        'roles': []
    }

    assert response.status_code == 200
    assert response.json() == {
        'account': expected_account_state
    }


def test_remove_role_unauthorized(monkeypatch):
    """
    It should fail to remove roles if the requesting account does not have permission.
    """
    def mock_get_account_by_email(email):
        if email == 'member@university.edu':
            return {
                'email': 'member@university.edu',
                'roles': ['member'],
                'authorizations': {
                    'can_do_x': True,
                    'can_do_y': True,
                    '_read': [],
                    '_write': []
                }
            }
        else:
            return {
                'email': 'admin@university.edu',
                'roles': ['admin'],
                'authorizations': {
                    'root': True,
                    '_read': ['admin, member'],
                    '_write': ['admin', 'member']
                }
            }

    def mock_update_account(account_data):
        return account_data

    monkeypatch.setattr(AuthDB,
                        'get_account_by_email',
                        mock_get_account_by_email)

    monkeypatch.setattr(AuthDB,
                        'update_account',
                        mock_update_account)

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
    def mock_get_account_by_email(email):
        if email == 'member@university.edu':
            return {
                'email': 'member@university.edu',
                'roles': ['member'],
                'authorizations': {
                    'can_do_x': True,
                    'can_do_y': True,
                    '_read': [],
                    '_write': []
                }
            }
        else:
            return {
                'email': 'admin@university.edu',
                'roles': ['admin'],
                'authorizations': {
                    'root': True,
                    '_read': ['admin, member'],
                    '_write': ['admin', 'member']
                }
            }

    def mock_update_account(account_data):
        return account_data

    monkeypatch.setattr(AuthDB,
                        'get_account_by_email',
                        mock_get_account_by_email)

    monkeypatch.setattr(AuthDB,
                        'update_account',
                        mock_update_account)

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

    expected_account_state = {
        'email': 'member@university.edu',
        'roles': ['admin']
    }

    assert response.status_code == 200
    assert response.json() == {
        'account': expected_account_state
    }


def test_add_and_remove_roles_unauthorized(monkeypatch):
    """
    It should be able to add and remove roles for an account.
    """
    def mock_get_account_by_email(email):
        if email == 'member@university.edu':
            return {
                'email': 'member@university.edu',
                'roles': ['member'],
                'authorizations': {
                    'can_do_x': True,
                    'can_do_y': True,
                    '_read': [],
                    '_write': []
                }
            }
        else:
            return {
                'email': 'admin@university.edu',
                'roles': ['admin'],
                'authorizations': {
                    'root': True,
                    '_read': ['admin, member'],
                    '_write': ['admin', 'member']
                }
            }

    def mock_update_account(account_data):
        return account_data

    monkeypatch.setattr(AuthDB,
                        'get_account_by_email',
                        mock_get_account_by_email)

    monkeypatch.setattr(AuthDB,
                        'update_account',
                        mock_update_account)

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
