"""Tests for the role metadata controller functions."""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

SECURITY_LIAISON = {'role': 'security-liaison', 'alias': 'Security Liaison', 'tags': ['User']}


@pytest.fixture(autouse=True)
def registered_tags(in_memory_role_collections):
    for name in ('User', 'Feature', 'Beta'):
        client.post('/role-tags', json={'name': name})


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
        {'role': 'admin', 'alias': None, 'tags': ['User']},
        {'role': 'viewer', 'alias': 'Viewer', 'tags': []},
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
    assert response.json() == {'role': 'viewer', 'alias': 'Viewer', 'tags': []}


def test_post_accepts_only_tags():
    response = save({'role': 'beta-search', 'tags': ['Feature']})

    assert response.status_code == 201
    assert response.json() == {'role': 'beta-search', 'alias': None, 'tags': ['Feature']}


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
    assert response.json() == {'role': 'viewer', 'alias': 'Viewer', 'tags': ['Feature']}


def test_post_with_null_clears_that_field():
    save({'role': 'viewer', 'alias': 'Viewer', 'tags': ['User']})

    response = save({'role': 'viewer', 'alias': None})

    assert response.status_code == 200
    assert response.json() == {'role': 'viewer', 'alias': None, 'tags': ['User']}


@pytest.mark.parametrize('cleared_tags', [None, []])
def test_post_with_null_or_empty_tags_clears_them(cleared_tags):
    save({'role': 'viewer', 'alias': 'Viewer', 'tags': ['User']})

    response = save({'role': 'viewer', 'tags': cleared_tags})

    assert response.json() == {'role': 'viewer', 'alias': 'Viewer', 'tags': []}


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

    assert response.json() == {'role': 'viewer', 'alias': 'Viewer', 'tags': []}


@pytest.mark.parametrize('body', [
    {'role': 'viewer'},
    {'role': 'viewer', 'tags': 'User'},
    {'role': 'viewer', 'tags': ['User', '  ']},
    {'role': 'viewer', 'alias': '   '},
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


def test_endpoints_do_not_touch_casbin(monkeypatch):
    from util.enforcer import enforcer

    def fail(*args, **kwargs):
        raise AssertionError('role metadata must not touch casbin')

    for method in ('enforce', 'add_policy', 'remove_policy', 'add_grouping_policy',
                   'remove_grouping_policy', 'get_policy', 'get_grouping_policy'):
        monkeypatch.setattr(enforcer, method, fail)

    client.post('/role-tags', json={'name': 'Temporary'})
    save({'role': 'viewer', 'alias': 'Viewer', 'tags': ['User']})
    client.get('/role-metadata')
    client.get('/role-metadata', params={'tag': 'User'})
    client.get('/role-metadata/viewer')
    client.delete('/role-metadata/viewer')
    client.get('/role-tags')
    client.delete('/role-tags/Temporary')


def test_role_names_containing_a_slash_work_in_the_path():
    save({'role': 'reports/viewer', 'alias': 'Reports Viewer'})

    assert client.get('/role-metadata/reports%2Fviewer').json()['role'] == 'reports/viewer'
    assert client.delete('/role-metadata/reports%2Fviewer').status_code == 204
