from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_index_message():
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {
        'message': 'Go to \'/docs\' to view the endpoints and their functions.'}
