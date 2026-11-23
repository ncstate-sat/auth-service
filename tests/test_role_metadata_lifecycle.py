"""Tests that role metadata is deleted once casbin no longer references its role."""

import os

import pytest
from fastapi.testclient import TestClient
from main import app
from models.Token import Token

client = TestClient(app)
os.environ["JWT_SECRET"] = "TEST_SECRET"

ROOT_ADMIN_EMAIL = 'root@university.edu'
ACCOUNT_EMAIL = 'pat@university.edu'


@pytest.fixture(autouse=True)
def signed_in_root_admin(monkeypatch, in_memory_role_collections, in_memory_casbin):
    monkeypatch.setenv('ROOT_ADMIN_EMAIL', ROOT_ADMIN_EMAIL)
    token = Token.generate_token({'email': ROOT_ADMIN_EMAIL})
    monkeypatch.setitem(client.headers, 'Authorization', f'Bearer {token}')


def save_alias(role):
    response = client.post('/role-metadata', json={'role': role, 'alias': role.title()})
    assert response.status_code == 201


def has_metadata(role):
    return client.get(f'/role-metadata/{role}').status_code == 200


def remove_permissions(role, *permissions):
    return client.put('/update-role-permissions', json={
        'role': role,
        'remove_permissions': [{'obj': obj, 'act': act} for obj, act in permissions],
    })


def test_removing_a_roles_last_permission_deletes_its_metadata(in_memory_casbin):
    in_memory_casbin.add_policy('editor', 'records', 'write')
    save_alias('editor')

    remove_permissions('editor', ('records', 'write'))

    assert not has_metadata('editor')


def test_removing_one_of_several_permissions_keeps_metadata(in_memory_casbin):
    in_memory_casbin.add_policy('editor', 'records', 'write')
    in_memory_casbin.add_policy('editor', 'records', 'read')
    save_alias('editor')

    remove_permissions('editor', ('records', 'write'))

    assert has_metadata('editor')


def test_role_kept_alive_by_an_account_keeps_metadata(in_memory_casbin):
    in_memory_casbin.add_policy('editor', 'records', 'write')
    in_memory_casbin.add_grouping_policy(ACCOUNT_EMAIL, 'editor')
    save_alias('editor')

    remove_permissions('editor', ('records', 'write'))

    assert has_metadata('editor')


def test_revoking_a_roles_last_account_deletes_its_metadata(in_memory_casbin):
    in_memory_casbin.add_grouping_policy(ACCOUNT_EMAIL, 'editor')
    save_alias('editor')

    client.put('/update-account-roles', json={'email': ACCOUNT_EMAIL, 'remove_roles': ['editor']})

    assert not has_metadata('editor')


def test_removing_the_only_inheritance_link_deletes_both_roles_metadata(in_memory_casbin):
    in_memory_casbin.add_grouping_policy('admin', 'editor')
    save_alias('admin')
    save_alias('editor')

    client.put('/update-role-inheritance',
               json={'role': 'admin', 'remove_inherited_roles': ['editor']})

    assert not has_metadata('admin')
    assert not has_metadata('editor')


def test_removing_an_inheritance_link_keeps_metadata_of_roles_that_still_exist(in_memory_casbin):
    in_memory_casbin.add_grouping_policy('admin', 'editor')
    in_memory_casbin.add_policy('editor', 'records', 'write')
    save_alias('admin')
    save_alias('editor')

    client.put('/update-role-inheritance',
               json={'role': 'admin', 'remove_inherited_roles': ['editor']})

    assert not has_metadata('admin')
    assert has_metadata('editor')


def test_a_removed_roles_alias_can_be_used_again(in_memory_casbin):
    in_memory_casbin.add_policy('editor', 'records', 'write')
    in_memory_casbin.add_policy('writer', 'records', 'write')
    client.post('/role-metadata', json={'role': 'editor', 'alias': 'Writer'})

    remove_permissions('editor', ('records', 'write'))
    response = client.post('/role-metadata', json={'role': 'writer', 'alias': 'Writer'})

    assert response.status_code == 201
