"""Tests for the impersonation controller and the guards around impersonation tokens."""

import logging
import os

import pytest
from fastapi.testclient import TestClient
from main import app
from models.Token import Token
from util.enforcer import enforcer

client = TestClient(app)
os.environ["JWT_SECRET"] = "TEST_SECRET"

IMPERSONATOR_EMAIL = 'support@university.edu'
TARGET_EMAIL = 'member@university.edu'
ROOT_ADMIN_EMAIL = 'root@university.edu'
SERVICE_ACCOUNT_EMAIL = 'worker@project.iam.gserviceaccount.com'


@pytest.fixture(autouse=True)
def stub_enforcer(monkeypatch):
    """Grants only the impersonator auth:impersonate and gives the target the member role."""
    monkeypatch.setenv('ROOT_ADMIN_EMAIL', ROOT_ADMIN_EMAIL)
    monkeypatch.setattr(enforcer, 'enforce', lambda sub, obj, act: (
        sub == IMPERSONATOR_EMAIL and (obj, act) == ('auth', 'impersonate')
    ))
    monkeypatch.setattr(enforcer, 'get_roles_for_user',
                        lambda email: ['member'] if email == TARGET_EMAIL else [])
    monkeypatch.setattr(enforcer, 'get_implicit_roles_for_user',
                        lambda email: ['member'] if email == TARGET_EMAIL else [])
    monkeypatch.setattr(enforcer, 'get_implicit_permissions_for_user',
                        lambda email: (
                            [['member', 'records', 'read']] if email == TARGET_EMAIL else []
                        ))


def bearer(payload):
    return {'Authorization': f'Bearer {Token.generate_token(payload)}'}


def impersonation_headers():
    return bearer({'email': TARGET_EMAIL, 'impersonated_by': IMPERSONATOR_EMAIL})


def test_impersonate_returns_only_an_access_token(caplog):
    with caplog.at_level(logging.INFO, logger='controllers.impersonation'):
        response = client.post('/impersonate', json={'email': TARGET_EMAIL},
                               headers=bearer({'email': IMPERSONATOR_EMAIL}))

    assert response.status_code == 200
    assert set(response.json()) == {'token'}

    payload = Token.decode_token(response.json()['token'])
    assert payload['email'] == TARGET_EMAIL
    assert payload['roles'] == ['member']
    assert payload['permissions'] == ['records:read']
    assert payload['account_type'] == 'user'
    assert payload['impersonated_by'] == IMPERSONATOR_EMAIL
    assert payload['token_type'] == 'access'
    assert f'{IMPERSONATOR_EMAIL} impersonated {TARGET_EMAIL}' in caplog.text


def test_impersonate_requires_permission(caplog):
    with caplog.at_level(logging.WARNING, logger='controllers.impersonation'):
        response = client.post('/impersonate', json={'email': TARGET_EMAIL},
                               headers=bearer({'email': 'someone@university.edu'}))

    assert response.status_code == 403
    assert 'token' not in response.json()
    assert f'someone@university.edu was denied impersonating {TARGET_EMAIL}' in caplog.text


@pytest.mark.parametrize('protected_email', [ROOT_ADMIN_EMAIL, SERVICE_ACCOUNT_EMAIL])
def test_impersonate_rejects_protected_accounts(protected_email):
    response = client.post('/impersonate', json={'email': protected_email},
                           headers=bearer({'email': IMPERSONATOR_EMAIL}))

    assert response.status_code == 403
    assert 'token' not in response.json()


def test_impersonate_rejects_invalid_email():
    response = client.post('/impersonate', json={'email': 'not-an-email'},
                           headers=bearer({'email': IMPERSONATOR_EMAIL}))

    assert response.status_code == 422


@pytest.mark.parametrize('method, path, body', [
    ('post', '/impersonate', {'email': 'other@university.edu'}),
    ('get', '/roles', None),
    ('get', f'/account?email={TARGET_EMAIL}', None),
    ('put', '/update-account-roles', {'email': TARGET_EMAIL, 'add_roles': ['admin']}),
    ('put', '/update-role-permissions', {'role': 'member', 'add_permissions': []}),
    ('put', '/update-role-inheritance', {'role': 'member', 'add_inherited_roles': []}),
])
def test_auth_service_rejects_impersonation_tokens(method, path, body):
    response = client.request(method, path, json=body, headers=impersonation_headers())

    assert response.status_code == 403


def test_auth_service_rejects_refresh_tokens_as_bearer_tokens():
    refresh_token = Token.generate_refresh_token(IMPERSONATOR_EMAIL)

    response = client.post('/impersonate', json={'email': TARGET_EMAIL},
                           headers={'Authorization': f'Bearer {refresh_token}'})

    assert response.status_code == 403
    assert 'token' not in response.json()


def test_access_tokens_cannot_claim_another_token_type():
    token = Token.generate_token({'email': TARGET_EMAIL, 'token_type': 'refresh'})

    assert Token.decode_token(token)['token_type'] == 'access'


def test_refresh_token_rejects_impersonation_and_access_tokens():
    impersonation_token = Token.generate_token(
        {'email': TARGET_EMAIL, 'impersonated_by': IMPERSONATOR_EMAIL}
    )
    access_token = Token.generate_token({'email': TARGET_EMAIL})

    for token in [impersonation_token, access_token]:
        response = client.post('/refresh-token', json={'token': token})

        assert response.status_code == 403
        assert 'refresh_token' not in response.json()


def test_reserved_name_cannot_be_used_as_a_role(monkeypatch):
    def fail_on_write(*_policy):
        pytest.fail('a reserved role name was written to casbin')

    monkeypatch.setattr(enforcer, 'add_grouping_policy', fail_on_write)
    monkeypatch.setattr(enforcer, 'add_policy', fail_on_write)
    root_headers = bearer({'email': ROOT_ADMIN_EMAIL})

    responses = [
        client.put('/update-account-roles', json={'email': TARGET_EMAIL, 'add_roles': ['auth']},
                   headers=root_headers),
        client.put('/update-role-permissions',
                   json={'role': 'auth', 'add_permissions': [{'obj': 'member', 'act': 'read'}]},
                   headers=root_headers),
        client.put('/update-role-inheritance',
                   json={'role': 'member', 'add_inherited_roles': ['auth']},
                   headers=root_headers),
        client.put('/update-role-inheritance',
                   json={'role': 'auth', 'add_inherited_roles': ['member']},
                   headers=root_headers),
    ]

    assert all(response.status_code == 400 for response in responses)


def test_role_updater_can_grant_reserved_permissions(monkeypatch):
    granted_policies = []
    monkeypatch.setattr(enforcer, 'enforce',
                        lambda sub, obj, act: (obj, act) == ('support', 'roleupdate'))
    monkeypatch.setattr(enforcer, 'add_policy', lambda *policy: granted_policies.append(policy))
    monkeypatch.setattr(enforcer, 'get_filtered_policy', lambda index, role: [])
    grant = {'role': 'support', 'add_permissions': [{'obj': 'auth', 'act': 'impersonate'}]}

    response = client.put('/update-role-permissions', json=grant,
                          headers=bearer({'email': IMPERSONATOR_EMAIL}))

    assert response.status_code == 200
    assert granted_policies == [('support', 'auth', 'impersonate')]
