"""Tests for the authorization controller functions."""

from fastapi.testclient import TestClient
from main import app
from models.Account import Account
from models.Token import Token

client = TestClient(app)

ADMIN_ACCOUNT = {
    'email': 'admin@ncsu.edu',
    'campus_id': '00101234',
    'authorizations': {
        'test-app': {
            '_read': {
                'superuser': True
            },
            '_write': {
                'superuser': True
            }
        }
    }
}

ADMIN_ACCOUNT_WITHOUT_PERMISSION = {
    'email': 'admin@ncsu.edu',
    'campus_id': '00101234',
    'authorizations': {
        'test-app': {}
    }
}

ACCOUNT_TO_BE_CHANGED = {
    'email': 'user@ncsu.edu',
    'campus_id': '200101234',
    'authorizations': {}
}


def test_get_authorizations(monkeypatch):
    """It should get a user's authorizations given a query."""

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT)
        else:
            return Account(ACCOUNT_TO_BE_CHANGED)

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.get(
        '/authorizations?app_id=test-app&db_filter=access&value=True',
                          headers={'Authorization': f'Bearer {token}'},
                          json={
                              'email': 'user@ncsu.edu',
                              'app_id': 'test-app',
                              'authorization': {'access': True}
                          })

    assert response.status_code == 200
    assert response.json() == {
        'accounts': []
    }


def test_get_authorizations_without_permission(monkeypatch):
    """
    It should fail to get a user's authorizations if the requester
    does not have permission.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_WITHOUT_PERMISSION)
        else:
            return Account(ACCOUNT_TO_BE_CHANGED)

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.get(
        '/authorizations?app_id=test-app&db_filter=access&value=True',
                          headers={'Authorization': f'Bearer {token}'},
                          json={
                              'email': 'user@ncsu.edu',
                              'app_id': 'test-app',
                              'authorization': {'access': True}
                          })

    assert response.status_code == 400


def test_update_authorization(monkeypatch):
    """It should ensure a user's authorizations can be updated."""

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT)
        else:
            return Account(ACCOUNT_TO_BE_CHANGED)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.put('/update-authorization',
                          headers={'Authorization': f'Bearer {token}'},
                          json={
                              'email': 'user@ncsu.edu',
                              'app_id': 'test-app',
                              'authorization': {'access': True}
                          })

    assert response.status_code == 200
    assert response.json() == {
        'authorizations': {
            'test-app': {
                'access': True
            }
        }
    }


def test_update_authorization_without_permission(monkeypatch):
    """
    It should fail to update a user's authorization if the requester
    does not have permission.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_WITHOUT_PERMISSION)
        else:
            return Account(ACCOUNT_TO_BE_CHANGED)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.put('/update-authorization',
                          headers={'Authorization': f'Bearer {token}'},
                          json={
                              'email': 'user@ncsu.edu',
                              'app_id': 'test-app',
                              'authorization': {'access': True}
                          })

    assert response.status_code == 400


def test_delete_authorization(monkeypatch):
    """It should ensure a user's authorization can be deleted."""

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT)
        else:
            return Account(ACCOUNT_TO_BE_CHANGED)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.delete(
        '/delete-authorization?app_id=test-app&email=user@ncsu.edu',
        headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    assert response.json() == {'authorizations': {}}


def test_delete_authorization_without_permission(monkeypatch):
    """
    It should fail to delete a user's authorizations if the requester
    does not have permission.
    """
    
    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_WITHOUT_PERMISSION)
        else:
            return Account(ACCOUNT_TO_BE_CHANGED)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT)
    response = client.delete(
        '/delete-authorization?app_id=test-app&email=user@ncsu.edu',
        headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400
