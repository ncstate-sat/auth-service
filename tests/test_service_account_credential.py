"""Tests for minting a service account credential from a JSON key."""

import io
import json

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.oauth2 import _client
from util.service_account_credential import main, mint_credential

SA_EMAIL = 'reports@project.iam.gserviceaccount.com'
AUDIENCE = 'https://auth.university.edu'
GOOGLE_ID_TOKEN = 'google.id.token'

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

KEY = {
    'type': 'service_account',
    'project_id': 'project',
    'private_key_id': 'abc123',
    'private_key': _private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode(),
    'client_email': SA_EMAIL,
    'client_id': '111111111111111111111',
    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
    'token_uri': 'https://oauth2.googleapis.com/token',
    'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
    'client_x509_cert_url': 'https://www.googleapis.com/robot/v1/metadata/x509/reports',
    'universe_domain': 'googleapis.com',
}


@pytest.fixture
def token_endpoint(monkeypatch):
    """Stubs Google's token endpoint, recording the signed assertions sent to it."""
    assertions = []

    def mock_id_token_jwt_grant(request, token_uri, assertion):
        assertions.append(jwt.decode(assertion, _private_key.public_key(), ['RS256'],
                                     audience=token_uri))
        return GOOGLE_ID_TOKEN, None, {}

    monkeypatch.setattr(_client, 'id_token_jwt_grant', mock_id_token_jwt_grant)
    return assertions


def test_mint_credential(token_endpoint):
    """It signs a request for an ID token with the requested audience, using the key."""
    assert mint_credential(KEY, AUDIENCE) == GOOGLE_ID_TOKEN
    assert mint_credential(json.dumps(KEY), AUDIENCE) == GOOGLE_ID_TOKEN

    [assertion, _] = token_endpoint
    assert assertion['iss'] == SA_EMAIL
    assert assertion['target_audience'] == AUDIENCE


def test_mint_credential_default_audience(monkeypatch, token_endpoint):
    """Without an audience, it uses the first audience this service accepts."""
    monkeypatch.setenv('GOOGLE_SERVICE_AUDIENCES', f'{AUDIENCE}, other-audience')

    mint_credential(KEY)

    assert token_endpoint[0]['target_audience'] == AUDIENCE


def test_mint_credential_rejects_other_keys():
    """It only accepts service account keys."""
    with pytest.raises(ValueError):
        mint_credential({**KEY, 'type': 'authorized_user'}, AUDIENCE)


def test_main(tmp_path, monkeypatch, capsys, token_endpoint):
    """The command line reads the key from a file or stdin and prints the credential."""
    key_file = tmp_path / 'key.json'
    key_file.write_text(json.dumps(KEY))

    main([str(key_file), '--audience', AUDIENCE])
    assert capsys.readouterr().out.strip() == GOOGLE_ID_TOKEN

    monkeypatch.setattr('sys.stdin', io.StringIO(json.dumps(KEY)))
    main(['-', '--audience', AUDIENCE])
    assert capsys.readouterr().out.strip() == GOOGLE_ID_TOKEN


def test_main_reports_errors(tmp_path):
    """The command line exits with a message instead of a traceback."""
    key_file = tmp_path / 'key.json'
    key_file.write_text(json.dumps({**KEY, 'type': 'authorized_user'}))

    with pytest.raises(SystemExit, match='Could not mint a credential'):
        main([str(key_file), '--audience', AUDIENCE])
