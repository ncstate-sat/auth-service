"""Tests for the role tags controller functions."""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

pytestmark = pytest.mark.usefixtures('in_memory_role_collections')


def create_tag(name):
    return client.post('/role-tags', json={'name': name})


def test_get_all_is_empty_without_tags():
    response = client.get('/role-tags')

    assert response.status_code == 200
    assert response.json() == {'role_tags': []}


def test_get_all_returns_tags_sorted_by_name():
    create_tag('User')
    create_tag('Feature')

    response = client.get('/role-tags')

    assert response.json() == {'role_tags': [{'name': 'Feature'}, {'name': 'User'}]}


def test_post_creates_tag():
    response = create_tag('Feature')

    assert response.status_code == 201
    assert response.json() == {'name': 'Feature'}


def test_post_trims_name():
    response = create_tag('  Feature ')

    assert response.json() == {'name': 'Feature'}


def test_post_rejects_existing_name():
    create_tag('Feature')

    response = create_tag('Feature')

    assert response.status_code == 409


def test_post_rejects_name_differing_only_by_case():
    create_tag('Feature')

    response = create_tag('FEATURE')

    assert response.status_code == 409
    assert '"Feature"' in response.json()['detail']


@pytest.mark.parametrize('body', [{}, {'name': '   '}, {'name': None}])
def test_post_rejects_invalid_body(body):
    response = client.post('/role-tags', json=body)

    assert response.status_code == 422


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
    assert client.get('/role-tags').json() == {'role_tags': [{'name': 'Feature'}]}


def test_delete_allowed_once_tag_is_removed_from_roles():
    create_tag('Feature')
    client.post('/role-metadata', json={'role': 'dark-mode', 'tags': ['Feature']})
    client.post('/role-metadata', json={'role': 'dark-mode', 'tags': []})

    response = client.delete('/role-tags/Feature')

    assert response.status_code == 204


def test_tag_names_containing_a_slash_work_in_the_path():
    create_tag('team/platform')

    assert client.delete('/role-tags/team%2Fplatform').status_code == 204
