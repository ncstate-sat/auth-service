"""Mints a Google ID token (the credential for /service-account/google-sign-in)
from a Google Cloud service account's JSON key.

This is for local testing and the demo website. Services running on Google
Cloud don't need a key file; `google.oauth2.id_token.fetch_id_token` gets the
same credential from the metadata server.

Usage:
    python -m util.service_account_credential path/to/key.json [--audience AUDIENCE]
    cat key.json | python -m util.service_account_credential - [--audience AUDIENCE]

The audience defaults to the first value accepted by this service (see
util.identity.service_account_audiences). The credential is printed to stdout.
"""

import argparse
import json
import sys

import google.auth.transport.requests
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account
from util.identity import service_account_audiences


def mint_credential(key, audience=None):
    """Returns a Google-signed ID token for the service account in the given key.

    :param key: The service account's JSON key, as a dict or a JSON string.
    :param audience: The token's 'aud'. Defaults to the first audience this service accepts.
    """
    key_info = json.loads(key) if isinstance(key, str) else key
    if key_info.get('type') != 'service_account':
        raise ValueError('The key must be a Google Cloud service account key '
                         '("type": "service_account").')

    credentials = service_account.IDTokenCredentials.from_service_account_info(
        key_info, target_audience=audience or service_account_audiences()[0])
    credentials.refresh(google.auth.transport.requests.Request())

    return credentials.token


def main(argv=None):
    parser = argparse.ArgumentParser(description=(
        'Print a Google ID token for a service account, to exchange at '
        '/service-account/google-sign-in.'))
    parser.add_argument('key_file', help='path to the JSON key file, or - to read it from stdin')
    parser.add_argument('--audience', help=('the token audience (defaults to '
                                            'GOOGLE_SERVICE_AUDIENCES or GOOGLE_CLIENT_ID)'))
    args = parser.parse_args(argv)

    if args.key_file == '-':
        key = sys.stdin.read()
    else:
        with open(args.key_file, encoding='utf-8') as key_file:
            key = key_file.read()

    audience = args.audience or service_account_audiences()[0]
    if not audience:
        parser.error('no audience: pass --audience, or set '
                     'GOOGLE_SERVICE_AUDIENCES or GOOGLE_CLIENT_ID')

    try:
        print(mint_credential(key, audience))
    except (ValueError, GoogleAuthError) as e:
        sys.exit(f'Could not mint a credential: {e}')


if __name__ == '__main__':
    main()
