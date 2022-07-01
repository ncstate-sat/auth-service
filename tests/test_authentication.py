from fastapi.testclient import TestClient
from main import app
from models.Account import Account
from models.Token import Token

client = TestClient(app)

EMAIL = 'user@ncsu.edu'
CAMPUS_ID = '200101234'


def test_decode_google_token(monkeypatch):
    def mock_decode_google_token(*args, **kwargs):
        return {'email': EMAIL}

    def mock_find_by_email(*args, **kwargs):
        return Account({'id': '62bc911d2947f5aa76600598', 'email': EMAIL, 'campus_id': CAMPUS_ID, 'authorizations': {}})

    monkeypatch.setattr(Token, 'decode_google_token', mock_decode_google_token)
    monkeypatch.setattr(Account, 'find_by_email', mock_find_by_email)

    response = client.post('/google-sign-in', json={'token': 'token'})
    assert response.status_code == 200
    assert 'token' in response.json()
    assert 'error' not in response.json()


def test_decode_token():
    token = Token.generate_token({'email': EMAIL})

    response = client.post(
        '/login', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 200
    assert response.json() == {'email': EMAIL}
