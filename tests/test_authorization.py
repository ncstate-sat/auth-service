"""Tests for the authorization controller functions."""

from fastapi.testclient import TestClient
from main import app
from models.Account import Account
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
    'email': 'admin@ncsu.edu',
    'campus_id': '00101234',
    'roles': ['admin']
}

MEMBER_ACCOUNT = {
    'email': 'member@ncsu.edu',
    'campus_id': '00101235',
    'roles': ['member']
}


def test_get_accounts_with_role(monkeypatch):
    """
    It should get all users with a role.
    """
    def mock_get_account_by_email(*_, **__):
        return {
            'email': 'admin@ncsu.edu',
            'campus_id': '00101234',
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
                'email': 'member@ncsu.edu',
                'campus_id': '00101235',
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


def test_get_account_with_role_unauthorized(monkeypatch):
    """
    It should fail to get users with a certain role if the requesting account does not have authorization.
    """
    def mock_get_account_by_email(*_, **__):
        return {
            'email': 'member@ncsu.edu',
            'campus_id': '00101235',
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
                'email': 'admin@ncsu.edu',
                'campus_id': '00101234',
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
        'error': 'This account is not authorized to write to this user\'s authorization(s).'
    }


def test_add_role(monkeypatch):
    """
    It should be able to add a role to an account.
    """
    def mock_get_account_by_email(email):
        if email == 'member@ncsu.edu':
            return {
                'email': 'member@ncsu.edu',
                'campus_id': '00101235',
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
                'email': 'admin@ncsu.edu',
                'campus_id': '00101234',
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


def test_add_role_unauthorized(monkeypatch):
    """
    It should fail to add roles to an account if the requesting account does not have authorization.
    """
    def mock_get_account_by_email(email):
        if email == 'member@ncsu.edu':
            return {
                'email': 'member@ncsu.edu',
                'campus_id': '00101235',
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
                'email': 'admin@ncsu.edu',
                'campus_id': '00101234',
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
        if email == 'member@ncsu.edu':
            return {
                'email': 'member@ncsu.edu',
                'campus_id': '00101235',
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
                'email': 'admin@ncsu.edu',
                'campus_id': '00101234',
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
        'email': 'member@ncsu.edu',
        'campus_id': '00101235',
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
        if email == 'member@ncsu.edu':
            return {
                'email': 'member@ncsu.edu',
                'campus_id': '00101235',
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
                'email': 'admin@ncsu.edu',
                'campus_id': '00101234',
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
        if email == 'member@ncsu.edu':
            return {
                'email': 'member@ncsu.edu',
                'campus_id': '00101235',
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
                'email': 'admin@ncsu.edu',
                'campus_id': '00101234',
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
        'email': 'member@ncsu.edu',
        'campus_id': '00101235',
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
        if email == 'member@ncsu.edu':
            return {
                'email': 'member@ncsu.edu',
                'campus_id': '00101235',
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
                'email': 'admin@ncsu.edu',
                'campus_id': '00101234',
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
