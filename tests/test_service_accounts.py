"""Tests for service account authentication."""

import os

from fastapi.testclient import TestClient
from main import app
from models.Account import Account
from models.Token import Token

client = TestClient(app)
os.environ["JWT_SECRET"] = "TEST_SECRET"

SA_EMAIL = 'reports@project.iam.gserviceaccount.com'
SA_SUB = '111111111111111111111'
USER_EMAIL = 'user@university.edu'


def mock_google_token(email, email_verified=True):
    """Builds a mock decode_google_token() that returns the given identity."""
    def _decode(*args, **kwargs):
        return {'email': email, 'sub': SA_SUB, 'email_verified': email_verified}
    return _decode


def mock_account(roles):
    """Builds a mock find_by_email() that returns an account with the given roles."""
    return lambda email: Account({'email': email, 'roles': roles, 'permissions': []})


def test_service_account_sign_in(monkeypatch):
    """A service account gets an auth token carrying its roles, and no refresh token."""
    monkeypatch.setattr(Token, 'decode_google_token', mock_google_token(SA_EMAIL))
    monkeypatch.setattr(Account, 'find_by_email', mock_account(['reporter']))

    response = client.post('/service-account/google-sign-in', json={'token': 'token'})

    assert response.status_code == 200
    assert 'token' in response.json()
    assert 'refresh_token' not in response.json()
    payload = Token.decode_token(response.json()['token'])
    assert payload['email'] == SA_EMAIL
    assert payload['roles'] == ['reporter']
    assert payload['account_type'] == 'service'


def test_service_account_sign_in_without_roles(monkeypatch):
    """Like a user, a service account with no roles still signs in, with no permissions."""
    monkeypatch.setattr(Token, 'decode_google_token', mock_google_token(SA_EMAIL))
    monkeypatch.setattr(Account, 'find_by_email', mock_account([]))

    response = client.post('/service-account/google-sign-in', json={'token': 'token'})

    assert response.status_code == 200
    payload = Token.decode_token(response.json()['token'])
    assert payload['roles'] == []
    assert payload['permissions'] == []


def test_service_account_sign_in_rejects_users(monkeypatch):
    """People sign in through /google-sign-in, not the service account endpoint."""
    monkeypatch.setattr(Token, 'decode_google_token', mock_google_token(USER_EMAIL))

    response = client.post('/service-account/google-sign-in', json={'token': 'token'})

    assert response.status_code == 403
    assert 'token' not in response.json()


def test_service_account_sign_in_invalid_credential(monkeypatch):
    """An invalid or unverified Google credential is rejected with a 401."""
    def mock_invalid(*args, **kwargs):
        raise ValueError('Token expired')

    monkeypatch.setattr(Token, 'decode_google_token', mock_invalid)
    response = client.post('/service-account/google-sign-in', json={'token': 'token'})
    assert response.status_code == 401

    monkeypatch.setattr(Token, 'decode_google_token',
                        mock_google_token(SA_EMAIL, email_verified=False))
    response = client.post('/service-account/google-sign-in', json={'token': 'token'})
    assert response.status_code == 401


def test_service_account_sign_in_audiences(monkeypatch):
    """Service account tokens are verified against GOOGLE_SERVICE_AUDIENCES."""
    audiences = []

    def mock_decode(token, audience=None):
        audiences.append(audience)
        return {'email': SA_EMAIL, 'sub': SA_SUB, 'email_verified': True}

    monkeypatch.setenv('GOOGLE_SERVICE_AUDIENCES', 'https://auth.university.edu, other-audience')
    monkeypatch.setattr(Token, 'decode_google_token', mock_decode)
    monkeypatch.setattr(Account, 'find_by_email', mock_account([]))

    client.post('/service-account/google-sign-in', json={'token': 'token'})

    assert audiences == [['https://auth.university.edu', 'other-audience']]


def test_user_sign_in_rejects_service_accounts(monkeypatch):
    """Service accounts can't get a user token (and refresh token) through /google-sign-in."""
    monkeypatch.setattr(Token, 'decode_google_token', mock_google_token(SA_EMAIL))

    response = client.post('/google-sign-in', json={'token': 'token'})

    assert response.status_code == 403
    assert 'token' not in response.json()


def test_refresh_token_rejects_service_accounts():
    """Service account tokens can't be exchanged at /refresh-token."""
    service_token = Token.generate_token({'email': SA_EMAIL, 'account_type': 'service'})

    response = client.post('/refresh-token', json={'token': service_token})

    assert response.status_code == 403
    assert 'token' not in response.json()
