"""Tests for the role metadata controller functions."""

import os

import pytest
from fastapi.testclient import TestClient
from main import app
from models.Token import Token
from util.enforcer import enforcer

client = TestClient(app)
os.environ["JWT_SECRET"] = "TEST_SECRET"

ROLE_MANAGER_EMAIL = 'manager@university.edu'
OTHER_EMAIL = 'other@university.edu'

SECURITY_LIAISON = {'role': 'security-liaison', 'alias': 'Security Liaison', 'tags': ['User'],
                    'description': 'Coordinates security reviews'}


@pytest.fixture(autouse=True)
def signed_in_role_manager(monkeypatch):
    """Signs requests in as an account allowed to do anything, unless a test sends other headers."""
    monkeypatch.setattr(enforcer, 'enforce', lambda sub, _obj, _act: sub == ROLE_MANAGER_EMAIL)
    monkeypatch.setitem(client.headers, 'Authorization',
                        bearer(ROLE_MANAGER_EMAIL)['Authorization'])


@pytest.fixture(autouse=True)
def registered_tags(in_memory_role_collections, signed_in_role_manager):
    for name in ('User', 'Feature', 'Beta'):
        client.post('/role-tags', json={'name': name})


def bearer(email):
    return {'Authorization': f'Bearer {Token.generate_token({"email": email})}'}


def grant_other_account(monkeypatch, *permissions):
    monkeypatch.setattr(enforcer, 'enforce', lambda sub, obj, act: (
        sub == ROLE_MANAGER_EMAIL or (sub == OTHER_EMAIL and f'{obj}:{act}' in permissions)))


def save(body):
    return client.post('/role-metadata', json=body)


def test_get_all_is_empty_without_metadata():
    response = client.get('/role-metadata')

    assert response.status_code == 200
    assert response.json() == {'role_metadata': []}


def test_get_all_returns_metadata_sorted_by_role():
    save({'role': 'viewer', 'alias': 'Viewer'})
    save({'role': 'admin', 'tags': ['User']})

    response = client.get('/role-metadata')

    assert response.json() == {'role_metadata': [
        {'role': 'admin', 'alias': None, 'tags': ['User'], 'description': None},
        {'role': 'viewer', 'alias': 'Viewer', 'tags': [], 'description': None},
    ]}


def test_get_one_returns_metadata():
    save(SECURITY_LIAISON)

    response = client.get('/role-metadata/security-liaison')

    assert response.status_code == 200
    assert response.json() == SECURITY_LIAISON


def test_get_one_without_metadata_is_404():
    response = client.get('/role-metadata/unknown-role')

    assert response.status_code == 404


def test_post_creates_metadata():
    response = save(SECURITY_LIAISON)

    assert response.status_code == 201
    assert response.json() == SECURITY_LIAISON


def test_post_accepts_only_an_alias():
    response = save({'role': 'viewer', 'alias': 'Viewer'})

    assert response.status_code == 201
    assert response.json() == {
        'role': 'viewer', 'alias': 'Viewer', 'tags': [], 'description': None}


def test_post_accepts_only_tags():
    response = save({'role': 'beta-search', 'tags': ['Feature']})

    assert response.status_code == 201
    assert response.json() == {
        'role': 'beta-search', 'alias': None, 'tags': ['Feature'], 'description': None}


def test_post_accepts_only_a_description():
    response = save({'role': 'viewer', 'description': 'Read-only access'})

    assert response.status_code == 201
    assert response.json() == {
        'role': 'viewer', 'alias': None, 'tags': [], 'description': 'Read-only access'}


def test_post_trims_description():
    response = save({'role': 'viewer', 'description': '  Read-only access '})

    assert response.json()['description'] == 'Read-only access'


def test_post_with_null_description_clears_it():
    save({'role': 'viewer', 'alias': 'Viewer', 'description': 'Read-only access'})

    response = save({'role': 'viewer', 'description': None})

    assert response.json() == {
        'role': 'viewer', 'alias': 'Viewer', 'tags': [], 'description': None}


def test_post_accepts_several_tags():
    response = save({'role': 'beta-search', 'tags': ['Feature', 'Beta']})

    assert response.json()['tags'] == ['Feature', 'Beta']


def test_post_removes_duplicate_tags_keeping_order():
    response = save({'role': 'beta-search', 'tags': ['Feature', 'Beta', 'Feature']})

    assert response.json()['tags'] == ['Feature', 'Beta']


def test_post_on_existing_role_updates_only_sent_fields():
    save({'role': 'viewer', 'alias': 'Viewer', 'tags': ['User']})

    response = save({'role': 'viewer', 'tags': ['Feature']})

    assert response.status_code == 200
    assert response.json() == {
        'role': 'viewer', 'alias': 'Viewer', 'tags': ['Feature'], 'description': None}


def test_post_with_null_clears_that_field():
    save({'role': 'viewer', 'alias': 'Viewer', 'tags': ['User']})

    response = save({'role': 'viewer', 'alias': None})

    assert response.status_code == 200
    assert response.json() == {
        'role': 'viewer', 'alias': None, 'tags': ['User'], 'description': None}


@pytest.mark.parametrize('cleared_tags', [None, []])
def test_post_with_null_or_empty_tags_clears_them(cleared_tags):
    save({'role': 'viewer', 'alias': 'Viewer', 'tags': ['User']})

    response = save({'role': 'viewer', 'tags': cleared_tags})

    assert response.json() == {
        'role': 'viewer', 'alias': 'Viewer', 'tags': [], 'description': None}


def test_post_rejects_unregistered_tags():
    response = save({'role': 'viewer', 'tags': ['User', 'Admin', 'Owner']})

    assert response.status_code == 422
    detail = response.json()['detail']
    assert '"Admin"' in detail and '"Owner"' in detail and '"User"' not in detail
    assert client.get('/role-metadata/viewer').status_code == 404


def test_post_requires_exact_tag_case():
    response = save({'role': 'viewer', 'tags': ['user']})

    assert response.status_code == 422


def test_post_trims_tags():
    response = save({'role': 'viewer', 'tags': ['  User ']})

    assert response.json()['tags'] == ['User']


def test_get_all_filters_by_tag():
    save({'role': 'viewer', 'tags': ['User']})
    save({'role': 'beta-search', 'tags': ['Feature', 'Beta']})
    save({'role': 'dark-mode', 'tags': ['Feature']})

    response = client.get('/role-metadata', params={'tag': 'Feature'})

    assert [entry['role'] for entry in response.json()['role_metadata']] == ['beta-search', 'dark-mode']


def test_cleared_alias_can_be_reused_by_another_role():
    save({'role': 'viewer', 'alias': 'Viewer'})
    save({'role': 'viewer', 'alias': None})

    response = save({'role': 'reader', 'alias': 'Viewer'})

    assert response.status_code == 201


def test_post_rejects_alias_used_by_another_role():
    save({'role': 'viewer', 'alias': 'Viewer'})

    response = save({'role': 'reader', 'alias': 'Viewer'})

    assert response.status_code == 409
    assert 'viewer' in response.json()['detail']


def test_post_rejects_alias_differing_only_by_case():
    save({'role': 'viewer', 'alias': 'Viewer'})

    response = save({'role': 'reader', 'alias': 'VIEWER'})

    assert response.status_code == 409


def test_post_allows_a_role_to_keep_its_own_alias():
    save({'role': 'viewer', 'alias': 'Viewer'})

    response = save({'role': 'viewer', 'alias': 'viewer'})

    assert response.status_code == 200
    assert response.json()['alias'] == 'viewer'


def test_post_trims_role_and_alias():
    response = save({'role': '  viewer ', 'alias': '  Viewer  '})

    assert response.json() == {
        'role': 'viewer', 'alias': 'Viewer', 'tags': [], 'description': None}


@pytest.mark.parametrize('body', [
    {'role': 'viewer'},
    {'role': 'viewer', 'tags': 'User'},
    {'role': 'viewer', 'tags': ['User', '  ']},
    {'role': 'viewer', 'alias': '   '},
    {'role': 'viewer', 'description': '   '},
    {'role': '   ', 'alias': 'Viewer'},
    {'role': 'person@university.edu', 'alias': 'Person'},
    {'alias': 'Viewer'},
])
def test_post_rejects_invalid_body(body):
    response = save(body)

    assert response.status_code == 422


def test_delete_removes_metadata():
    save({'role': 'viewer', 'alias': 'Viewer'})

    response = client.delete('/role-metadata/viewer')

    assert response.status_code == 204
    assert client.get('/role-metadata/viewer').status_code == 404


def test_delete_without_metadata_is_404():
    response = client.delete('/role-metadata/unknown-role')

    assert response.status_code == 404


def test_endpoints_do_not_write_to_casbin(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError('role metadata must not write to casbin')

    for method in ('add_policy', 'remove_policy', 'add_grouping_policy',
                   'remove_grouping_policy'):
        monkeypatch.setattr(enforcer, method, fail)

    client.post('/role-tags', json={'name': 'Temporary'})
    save({'role': 'viewer', 'alias': 'Viewer', 'tags': ['User']})
    client.get('/role-metadata')
    client.get('/role-metadata', params={'tag': 'User'})
    client.get('/role-metadata/viewer')
    client.delete('/role-metadata/viewer')
    client.get('/role-tags')
    client.patch('/role-tags/Temporary', json={'description': 'Short-lived'})
    client.delete('/role-tags/Temporary')


def test_role_names_containing_a_slash_work_in_the_path():
    save({'role': 'reports/viewer', 'alias': 'Reports Viewer'})

    assert client.get('/role-metadata/reports%2Fviewer').json()['role'] == 'reports/viewer'
    assert client.delete('/role-metadata/reports%2Fviewer').status_code == 204


def test_get_all_includes_only_roles_the_account_can_read(monkeypatch):
    save(SECURITY_LIAISON)
    save({'role': 'viewer', 'alias': 'Viewer', 'tags': ['User']})
    grant_other_account(monkeypatch, 'security-liaison:read', 'viewer:roleupdate')

    response = client.get('/role-metadata', headers=bearer(OTHER_EMAIL))
    filtered_response = client.get('/role-metadata', params={'tag': 'User'},
                                   headers=bearer(OTHER_EMAIL))

    assert response.json() == {'role_metadata': [SECURITY_LIAISON]}
    assert filtered_response.json() == {'role_metadata': [SECURITY_LIAISON]}


def test_get_one_requires_read_on_the_role(monkeypatch):
    save(SECURITY_LIAISON)
    grant_other_account(monkeypatch, 'security-liaison:roleupdate', 'viewer:read')

    response = client.get('/role-metadata/security-liaison', headers=bearer(OTHER_EMAIL))

    assert response.status_code == 403


def test_get_one_without_read_is_403_even_without_metadata(monkeypatch):
    grant_other_account(monkeypatch)

    response = client.get('/role-metadata/unknown-role', headers=bearer(OTHER_EMAIL))

    assert response.status_code == 403


def test_get_one_allowed_with_read_on_the_role(monkeypatch):
    save(SECURITY_LIAISON)
    grant_other_account(monkeypatch, 'security-liaison:read')

    response = client.get('/role-metadata/security-liaison', headers=bearer(OTHER_EMAIL))

    assert response.json() == SECURITY_LIAISON


def test_post_requires_roleupdate_on_the_role(monkeypatch):
    grant_other_account(monkeypatch, 'viewer:read', 'viewer:assign', 'reader:roleupdate')

    response = client.post('/role-metadata', json={'role': 'viewer', 'alias': 'Viewer'},
                           headers=bearer(OTHER_EMAIL))

    assert response.status_code == 403
    assert client.get('/role-metadata/viewer').status_code == 404


def test_post_allowed_with_roleupdate_on_the_role(monkeypatch):
    grant_other_account(monkeypatch, 'viewer:roleupdate')

    response = client.post('/role-metadata', json={'role': 'viewer', 'tags': ['User']},
                           headers=bearer(OTHER_EMAIL))

    assert response.status_code == 201


def test_delete_requires_roleupdate_on_the_role(monkeypatch):
    save({'role': 'viewer', 'alias': 'Viewer'})
    grant_other_account(monkeypatch, 'reader:roleupdate')

    response = client.delete('/role-metadata/viewer', headers=bearer(OTHER_EMAIL))

    assert response.status_code == 403
    assert client.get('/role-metadata/viewer').status_code == 200


def test_delete_allowed_with_roleupdate_on_the_role(monkeypatch):
    save({'role': 'viewer', 'alias': 'Viewer'})
    grant_other_account(monkeypatch, 'viewer:roleupdate')

    response = client.delete('/role-metadata/viewer', headers=bearer(OTHER_EMAIL))

    assert response.status_code == 204


def test_root_admin_can_save_and_delete_any_metadata(monkeypatch):
    root_admin_email = 'root@university.edu'
    monkeypatch.setenv('ROOT_ADMIN_EMAIL', root_admin_email)
    monkeypatch.setattr(enforcer, 'enforce', lambda *_request: False)

    save_response = client.post('/role-metadata', json={'role': 'viewer', 'alias': 'Viewer'},
                                headers=bearer(root_admin_email))
    delete_response = client.delete('/role-metadata/viewer', headers=bearer(root_admin_email))

    assert save_response.status_code == 201
    assert delete_response.status_code == 204
