"""Tests for the role tags controller functions."""

import os

import pytest
from fastapi.testclient import TestClient
from main import app
from models.Token import Token
from util.enforcer import enforcer

client = TestClient(app)
os.environ["JWT_SECRET"] = "TEST_SECRET"

pytestmark = pytest.mark.usefixtures('in_memory_role_collections')

TAG_MANAGER_EMAIL = 'tag-manager@university.edu'
OTHER_EMAIL = 'other@university.edu'
ROOT_ADMIN_EMAIL = 'root@university.edu'


@pytest.fixture(autouse=True)
def signed_in_tag_manager(monkeypatch):
    """Signs requests in as an account with auth:managetags, unless a test passes other headers."""
    monkeypatch.setenv('ROOT_ADMIN_EMAIL', ROOT_ADMIN_EMAIL)
    monkeypatch.setattr(enforcer, 'enforce', lambda sub, obj, act: (
        sub == TAG_MANAGER_EMAIL and (obj, act) in {('auth', 'managetags'),
                                                    ('dark-mode', 'roleupdate'),
                                                    ('dark-mode', 'read'),
                                                    ('beta-search', 'roleupdate')}))
    monkeypatch.setitem(client.headers, 'Authorization',
                        bearer(TAG_MANAGER_EMAIL)['Authorization'])


def bearer(email):
    return {'Authorization': f'Bearer {Token.generate_token({"email": email})}'}


def create_tag(name, description=None):
    return client.post('/role-tags', json={'name': name, 'description': description})


def test_get_all_is_empty_without_tags():
    response = client.get('/role-tags')

    assert response.status_code == 200
    assert response.json() == {'role_tags': []}


def test_get_all_returns_tags_sorted_by_name():
    create_tag('User')
    create_tag('Feature')

    response = client.get('/role-tags')

    assert response.json() == {'role_tags': [
        {'name': 'Feature', 'description': None}, {'name': 'User', 'description': None}]}


def test_post_creates_tag():
    response = create_tag('Feature')

    assert response.status_code == 201
    assert response.json() == {'name': 'Feature', 'description': None}


def test_post_creates_tag_with_description():
    response = create_tag('Feature', '  Roles that act as feature flags ')

    assert response.status_code == 201
    assert response.json() == {
        'name': 'Feature', 'description': 'Roles that act as feature flags'}
    assert client.get('/role-tags').json() == {'role_tags': [response.json()]}


def test_post_trims_name():
    response = create_tag('  Feature ')

    assert response.json() == {'name': 'Feature', 'description': None}


def test_post_rejects_existing_name():
    create_tag('Feature')

    response = create_tag('Feature')

    assert response.status_code == 409


def test_post_rejects_name_differing_only_by_case():
    create_tag('Feature')

    response = create_tag('FEATURE')

    assert response.status_code == 409
    assert '"Feature"' in response.json()['detail']


@pytest.mark.parametrize('body', [
    {}, {'name': '   '}, {'name': None}, {'name': 'Feature', 'description': '   '}])
def test_post_rejects_invalid_body(body):
    response = client.post('/role-tags', json=body)

    assert response.status_code == 422


def test_patch_sets_description():
    create_tag('Feature')

    response = client.patch('/role-tags/Feature', json={'description': '  Feature flags '})

    assert response.status_code == 200
    assert response.json() == {'name': 'Feature', 'description': 'Feature flags'}
    assert client.get('/role-tags').json() == {'role_tags': [response.json()]}


def test_patch_replaces_description():
    create_tag('Feature', 'Feature flags')

    response = client.patch('/role-tags/Feature', json={'description': 'Experiments'})

    assert response.json() == {'name': 'Feature', 'description': 'Experiments'}


def test_patch_with_null_clears_description():
    create_tag('Feature', 'Feature flags')

    response = client.patch('/role-tags/Feature', json={'description': None})

    assert response.status_code == 200
    assert response.json() == {'name': 'Feature', 'description': None}


def test_patch_unknown_tag_is_404():
    response = client.patch('/role-tags/Feature', json={'description': 'Feature flags'})

    assert response.status_code == 404


def test_patch_requires_exact_case():
    create_tag('Feature')

    response = client.patch('/role-tags/feature', json={'description': 'Feature flags'})

    assert response.status_code == 404


@pytest.mark.parametrize('body', [{}, {'description': '   '}, {'description': 5}])
def test_patch_rejects_invalid_body(body):
    create_tag('Feature')

    response = client.patch('/role-tags/Feature', json=body)

    assert response.status_code == 422


def test_patch_keeps_tag_assigned_to_roles():
    create_tag('Feature')
    client.post('/role-metadata', json={'role': 'dark-mode', 'tags': ['Feature']})

    client.patch('/role-tags/Feature', json={'description': 'Feature flags'})

    assert client.get('/role-metadata/dark-mode').json()['tags'] == ['Feature']


def test_delete_removes_unused_tag():
    create_tag('Feature')

    response = client.delete('/role-tags/Feature')

    assert response.status_code == 204
    assert client.get('/role-tags').json() == {'role_tags': []}


def test_delete_unknown_tag_is_404():
    response = client.delete('/role-tags/Feature')

    assert response.status_code == 404


def test_delete_requires_exact_case():
    create_tag('Feature')

    response = client.delete('/role-tags/feature')

    assert response.status_code == 404


def test_delete_rejects_tag_assigned_to_roles():
    create_tag('Feature')
    client.post('/role-metadata', json={'role': 'dark-mode', 'tags': ['Feature']})
    client.post('/role-metadata', json={'role': 'beta-search', 'tags': ['Feature']})

    response = client.delete('/role-tags/Feature')

    assert response.status_code == 409
    assert response.json()['detail']['roles'] == ['beta-search', 'dark-mode']
    assert client.get('/role-tags').json() == {
        'role_tags': [{'name': 'Feature', 'description': None}]}


def test_delete_allowed_once_tag_is_removed_from_roles():
    create_tag('Feature')
    client.post('/role-metadata', json={'role': 'dark-mode', 'tags': ['Feature']})
    client.post('/role-metadata', json={'role': 'dark-mode', 'tags': []})

    response = client.delete('/role-tags/Feature')

    assert response.status_code == 204


def test_tag_names_containing_a_slash_work_in_the_path():
    create_tag('team/platform')

    response = client.patch('/role-tags/team%2Fplatform', json={'description': 'Platform team'})

    assert response.json() == {'name': 'team/platform', 'description': 'Platform team'}
    assert client.delete('/role-tags/team%2Fplatform').status_code == 204


TAG_ENDPOINTS = [
    ('get', '/role-tags', None),
    ('post', '/role-tags', {'name': 'Beta'}),
    ('patch', '/role-tags/Feature', {'description': 'Feature flags'}),
    ('delete', '/role-tags/Feature', None),
]


@pytest.mark.parametrize('method, path, body', TAG_ENDPOINTS)
def test_every_endpoint_requires_managetags(monkeypatch, method, path, body):
    create_tag('Feature')
    monkeypatch.setattr(enforcer, 'enforce', lambda sub, obj, act: (
        sub == TAG_MANAGER_EMAIL or (sub == OTHER_EMAIL and act == 'roleupdate')))

    response = client.request(method, path, json=body, headers=bearer(OTHER_EMAIL))

    assert response.status_code == 403
    assert client.get('/role-tags').json() == {
        'role_tags': [{'name': 'Feature', 'description': None}]}


@pytest.mark.parametrize('method, path, body', TAG_ENDPOINTS)
def test_root_admin_can_use_every_endpoint(monkeypatch, method, path, body):
    create_tag('Feature')
    monkeypatch.setattr(enforcer, 'enforce', lambda *_request: False)

    response = client.request(method, path, json=body, headers=bearer(ROOT_ADMIN_EMAIL))

    assert response.status_code < 300
