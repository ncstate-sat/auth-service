from fastapi.testclient import TestClient
from main import app
from models.Account import Account
from models.Token import Token

client = TestClient(app)

EMAIL = 'user@ncsu.edu'
CAMPUS_ID = '200101234'


def test_update_authorization(monkeypatch):
    def mock_find_by_email(*args, **kwargs):
        return Account({'id': '62bc911d2947f5aa76600598', 'email': EMAIL, 'campus_id': CAMPUS_ID, 'authorizations': {}})

    def mock_update(*args, **kwargs):
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token({'email': EMAIL, 'campus_id': CAMPUS_ID})
    response = client.put('/update-authorization', headers={'Authorization': f'Bearer {token}'}, json={
                          'app_id': 'test-app', 'authorization': {'access': True}})
    assert response.status_code == 200
    assert response.json() == {
        'authorizations': {
            'test-app': {
                'access': True
            }
        }
    }


def test_delete_authorization(monkeypatch):
    def mock_find_by_email(*args, **kwargs):
        return Account({'id': '62bc911d2947f5aa76600598', 'email': EMAIL, 'campus_id': CAMPUS_ID, 'authorizations': {'test-app': {'access': True}}})

    def mock_update(*args, **kwargs):
        return

    monkeypatch.setattr(Account, "find_by_email", mock_find_by_email)
    monkeypatch.setattr(Account, "update", mock_update)

    token = Token.generate_token({'email': EMAIL, 'campus_id': CAMPUS_ID})
    response = client.delete(
        '/delete-authorization/test-app', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert response.json() == {'authorizations': {}}
