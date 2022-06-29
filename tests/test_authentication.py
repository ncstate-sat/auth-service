from fastapi.testclient import TestClient
from main import app
from models.Token import Token

client = TestClient(app)


def test_decode_google_token(monkeypatch):
    def mock_decode_google_token(*args, **kwargs):
        return {'email': 'test_user@ncsu.edu'}

    monkeypatch.setattr(Token, "decode_google_token", mock_decode_google_token)

    response = client.post('/google-sign-in', json={'token': 'token'})
    assert response.status_code == 200
    assert 'token' in response.json()
    assert 'error' not in response.json()


def test_decode_token():
    token = Token.generate_token({'email': 'test_user@ncsu.edu'})

    response = client.post(
        '/login', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 200
    assert response.json() == {'email': 'test_user@ncsu.edu'}
