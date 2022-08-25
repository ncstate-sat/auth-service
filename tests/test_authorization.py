"""Tests for the authorization controller functions."""

from fastapi.testclient import TestClient
from main import app
from models.Account import Account
from models.Token import Token

client = TestClient(app)

ADMIN_ACCOUNT_FULL_PERMISSION = {
    'email': 'admin@ncsu.edu',
    'campus_id': '00101234',
    'authorizations': {
        'test-app': {
            'access': True,
            '_read': {
                '_superuser': True
            },
            '_write': {
                '_superuser': True
            }
        }
    }
}

ADMIN_ACCOUNT_SOME_PERMISSION = {
    'email': 'admin@ncsu.edu',
    'campus_id': '00101234',
    'authorizations': {
        'test-app': {
            'access': True,
            '_read': {
                'access': True
            },
            '_write': {
                'access': True
            }
        }
    }
}

ADMIN_ACCOUNT_WRONG_PERMISSION = {
    'email': 'admin@ncsu.edu',
    'campus_id': '00101234',
    'authorizations': {
        'test-app': {
            'access': True,
            '_read': {
                'wrong-key': True
            },
            '_write': {
                'wrong-key': True
            }
        }
    }
}

ADMIN_ACCOUNT_NO_PERMISSION = {
    'email': 'admin@ncsu.edu',
    'campus_id': '00101234',
    'authorizations': {
        'test-app': {
            'access': True,
        }
    }
}

REGULAR_ACCOUNT_NO_AUTHORIZATIONS = {
    'email': 'user@ncsu.edu',
    'campus_id': '200101234',
    'authorizations': {}
}


def test_get_authorizations(monkeypatch):
    """It should get a user's authorizations given a query."""

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_FULL_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_find_by_authorization(*_, **__):
        return [Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)]

    monkeypatch.setattr(Account,
                        "find_by_email",
                        mock_find_by_email)
    monkeypatch.setattr(Account,
                        "find_by_authorization",
                        mock_find_by_authorization)

    token = Token.generate_token(ADMIN_ACCOUNT_FULL_PERMISSION)
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
        'accounts': [REGULAR_ACCOUNT_NO_AUTHORIZATIONS]
    }


def test_get_authorizations_with_some_permission(monkeypatch):
    """
    It should get a user's authorizations given a query with an
    admin account that does not have superuser permissions.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_SOME_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_find_by_authorization(*_, **__):
        return [Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)]

    monkeypatch.setattr(Account,
                        "find_by_email",
                        mock_find_by_email)
    monkeypatch.setattr(Account,
                        "find_by_authorization",
                        mock_find_by_authorization)

    token = Token.generate_token(ADMIN_ACCOUNT_SOME_PERMISSION)
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
        'accounts': [REGULAR_ACCOUNT_NO_AUTHORIZATIONS]
    }


def test_get_authorizations_with_wrong_permission(monkeypatch):
    """
    It should not be able to get a user's authorizations
    with an admin account that has the wrong permissions.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_WRONG_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_find_by_authorization(*_, **__):
        return [Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)]

    monkeypatch.setattr(Account,
                        "find_by_email",
                        mock_find_by_email)
    monkeypatch.setattr(Account,
                        "find_by_authorization",
                        mock_find_by_authorization)

    token = Token.generate_token(ADMIN_ACCOUNT_WRONG_PERMISSION)
    response = client.get(
        '/authorizations?app_id=test-app&db_filter=access&value=True',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': 'user@ncsu.edu',
            'app_id': 'test-app',
            'authorization': {'access': True}
        })

    assert response.status_code == 400


def test_get_authorizations_without_permission(monkeypatch):
    """
    It should fail to get a user's authorizations if the requester
    does not have permission.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_NO_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_find_by_authorization(*_, **__):
        return [Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)]

    monkeypatch.setattr(Account,
                        "find_by_email",
                        mock_find_by_email)
    monkeypatch.setattr(Account,
                        "find_by_authorization",
                        mock_find_by_authorization)

    token = Token.generate_token(ADMIN_ACCOUNT_NO_PERMISSION)
    response = client.get(
        '/authorizations?app_id=test-app&db_filter=access&value=True',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'email': 'user@ncsu.edu',
            'app_id': 'test-app',
            'authorization': {'access': True}
        })

    assert response.status_code == 400


def test_add_update_authorization(monkeypatch):
    """It should ensure a user's authorizations can be added to."""

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_FULL_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_FULL_PERMISSION)
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
                'access': True,
                '_read': {},
                '_write': {}
            }
        }
    }


def test_subtract_update_authorization(monkeypatch):
    """It should ensure a user's authorizations can be subtracted from."""

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_FULL_PERMISSION)
        else:
            return Account({
                'email': 'user@ncsu.edu',
                'campus_id': '200101234',
                'authorizations': {
                    'test-app': {
                        'access': True
                    }
                }
            })

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_FULL_PERMISSION)
    response = client.put('/update-authorization',
                        headers={'Authorization': f'Bearer {token}'},
                        json={
                            'email': 'user@ncsu.edu',
                            'app_id': 'test-app',
                            'authorization': {
                                'access': False
                            }
                        })

    assert response.status_code == 200
    assert response.json() == {
        'authorizations': {
            'test-app': {
                'access': False,
                '_read': {},
                '_write': {}
            }
        }
    }


def test_add_update_authorization_with_some_permission(monkeypatch):
    """
    It should add to a user's authorizations with an admin account that
    does not have superuser permissions.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_SOME_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_SOME_PERMISSION)
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
                'access': True,
                '_read': {},
                '_write': {}
            }
        }
    }


def test_subtract_update_authorization_with_some_permission(monkeypatch):
    """
    It should subtract from a user's authorizations with an admin
    account that does not have superuser permissions.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_SOME_PERMISSION)
        else:
            return Account({
                'email': 'user@ncsu.edu',
                'campus_id': '200101234',
                'authorizations': {
                    'test-app': {
                        'access': True
                    }
                }
            })

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_SOME_PERMISSION)
    response = client.put('/update-authorization',
                        headers={'Authorization': f'Bearer {token}'},
                        json={
                            'email': 'user@ncsu.edu',
                            'app_id': 'test-app',
                            'authorization': {
                                'access': False
                            }
                        })

    assert response.status_code == 200
    assert response.json() == {
        'authorizations': {
            'test-app': {
                'access': False,
                '_read': {},
                '_write': {}
            }
        }
    }


def test_add_update_authorization_with_wrong_permission(monkeypatch):
    """
    It should not be able to add to a user's authorizations
    with an admin account that has the wrong permissions.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_WRONG_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_WRONG_PERMISSION)
    response = client.put('/update-authorization',
                          headers={'Authorization': f'Bearer {token}'},
                          json={
                              'email': 'user@ncsu.edu',
                              'app_id': 'test-app',
                              'authorization': {'access': True}
                          })

    assert response.status_code == 400


def test_subtract_update_authorization_with_wrong_permission(monkeypatch):
    """
    It should not be able to subtract from a user's authorizations
    with an admin account that has the wrong permissions.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_WRONG_PERMISSION)
        else:
            return Account({
                'email': 'user@ncsu.edu',
                'campus_id': '200101234',
                'authorizations': {
                    'test-app': {
                        'access': True
                    }
                }
            })

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_WRONG_PERMISSION)
    response = client.put('/update-authorization',
                          headers={'Authorization': f'Bearer {token}'},
                          json={
                              'email': 'user@ncsu.edu',
                              'app_id': 'test-app',
                              'authorization': {}
                          })

    assert response.status_code == 400


def test_add_update_authorization_without_permission(monkeypatch):
    """
    It should fail to add to a user's authorizations if the requester
    does not have permission.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_NO_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_NO_PERMISSION)
    response = client.put('/update-authorization',
                          headers={'Authorization': f'Bearer {token}'},
                          json={
                              'email': 'user@ncsu.edu',
                              'app_id': 'test-app',
                              'authorization': {'access': True}
                          })

    assert response.status_code == 400


def test_subtract_update_authorization_without_permission(monkeypatch):
    """
    It should fail to subtract from a user's authorizations if the requester
    does not have permission.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_NO_PERMISSION)
        else:
            return Account({
                'email': 'user@ncsu.edu',
                'campus_id': '200101234',
                'authorizations': {
                    'test-app': {
                        'access': True
                    }
                }
            })

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_NO_PERMISSION)
    response = client.put('/update-authorization',
                          headers={'Authorization': f'Bearer {token}'},
                          json={
                              'email': 'user@ncsu.edu',
                              'app_id': 'test-app',
                              'authorization': {}
                          })

    assert response.status_code == 400


def test_delete_authorization(monkeypatch):
    """It should ensure a user's authorization can be deleted."""

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_FULL_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_FULL_PERMISSION)
    response = client.delete(
        '/delete-authorization?app_id=test-app&email=user@ncsu.edu',
        headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    assert response.json() == {'authorizations': {}}


def test_delete_authorization_with_some_permission(monkeypatch):
    """
    It should fail to delete a user's authorizations if the requester
    does not have superuser permission.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_SOME_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_SOME_PERMISSION)
    response = client.delete(
        '/delete-authorization?app_id=test-app&email=user@ncsu.edu',
        headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400


def test_delete_authorization_with_wrong_permission(monkeypatch):
    """
    It should fail to delete a user's authorizations if the requester
    does not have superuser permission.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_WRONG_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_WRONG_PERMISSION)
    response = client.delete(
        '/delete-authorization?app_id=test-app&email=user@ncsu.edu',
        headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400


def test_delete_authorization_without_permission(monkeypatch):
    """
    It should fail to delete a user's authorizations if the requester
    does not have superuser permission.
    """

    def mock_find_by_email(email):
        """Mock Account.find_by_email function."""
        if email == 'admin@ncsu.edu':
            return Account(ADMIN_ACCOUNT_NO_PERMISSION)
        else:
            return Account(REGULAR_ACCOUNT_NO_AUTHORIZATIONS)

    def mock_update(*_, **__):
        """Mock Account.update function."""
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token(ADMIN_ACCOUNT_NO_PERMISSION)
    response = client.delete(
        '/delete-authorization?app_id=test-app&email=user@ncsu.edu',
        headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400
