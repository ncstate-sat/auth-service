import os
from fastapi.testclient import TestClient
from main import app
from models.Account import Account
from models.Token import Token


client = TestClient(app)
os.environ["JWT_SECRET"] = "TEST_SECRET"

EMAIL = 'user@university.edu'
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


def test_decode_google_token(monkeypatch):
    def mock_decode_google_token(*args, **kwargs):
        return {'email': EMAIL}

    def mock_find_by_email(*args, **kwargs):
        return Account({'email': EMAIL, 'authorizations': {}})

    monkeypatch.setattr(Token, 'decode_google_token', mock_decode_google_token)
    monkeypatch.setattr(Account, 'find_by_email', mock_find_by_email)

    response = client.post('/google-sign-in', json={'token': 'token'})
    assert response.status_code == 200
    assert 'token' in response.json()
    assert 'refresh_token' in response.json()
    assert 'error' not in response.json()


def test_decode_token():
    valid_token = Token.generate_token({'email': EMAIL})
    response = client.post(
        '/login', headers={'Authorization': 'Bearer ' + valid_token})
    assert response.status_code == 200
    assert 'email' in response.json()

    expired_response = client.post(
        '/login', headers={'Authorization': 'Bearer ' + EXPIRED_JWT})
    assert expired_response.status_code == 401
    assert 'email' not in expired_response.json()

    bad_signature_response = client.post(
        '/login', headers={'Authorization': 'Bearer ' + INVALID_SIGNATURE_JWT})
    assert bad_signature_response.status_code == 400
    assert 'email' not in expired_response.json()


def test_refresh_token(monkeypatch):
    def mock_find_by_email(*args, **kwargs):
        return Account({'email': EMAIL, 'authorizations': {}})

    monkeypatch.setattr(Account, 'find_by_email', mock_find_by_email)

    refresh_token = Token.generate_refresh_token({'email': EMAIL})

    response = client.post('/refresh-token',
                           json={'token': refresh_token})
    assert response.status_code == 200
    assert 'token' in response.json()
    assert 'refresh_token' in response.json()

    response = client.post('/refresh-token',
                           json={'token': EXPIRED_JWT})
    assert response.status_code == 401
    assert 'token' not in response.json()
    assert 'refresh_token' not in response.json()

    response = client.post('/refresh-token',
                           json={'token': INVALID_SIGNATURE_JWT})
    assert response.status_code == 400
    assert 'token' not in response.json()
    assert 'refresh_token' not in response.json()
