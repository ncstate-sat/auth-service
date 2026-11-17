"""Mints a Google ID token (the credential for /service-account/google-sign-in)
from a Google Cloud service account's JSON key.

This is for local testing and the demo website. Services running on Google
Cloud don't need a key file; `google.oauth2.id_token.fetch_id_token` gets the
same credential from the metadata server.

Usage:
    python -m util.service_account_credential path/to/key.json
    cat key.json | python -m util.service_account_credential -

The token's audience is GOOGLE_CLIENT_ID, which must be set. The credential
is printed to stdout.
"""

import argparse
import json
import os
import sys

import google.auth.transport.requests
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account


def mint_credential(key):
    """Returns a Google-signed ID token for the service account in the given key,
    with GOOGLE_CLIENT_ID as its audience.

    :param key: The service account's JSON key, as a dict or a JSON string.
    """
    key_info = json.loads(key) if isinstance(key, str) else key
    if key_info.get('type') != 'service_account':
        raise ValueError('The key must be a Google Cloud service account key '
                         '("type": "service_account").')

    audience = os.getenv('GOOGLE_CLIENT_ID')
    if not audience:
        raise ValueError('GOOGLE_CLIENT_ID must be set.')

    credentials = service_account.IDTokenCredentials.from_service_account_info(
        key_info, target_audience=audience)
    credentials.refresh(google.auth.transport.requests.Request())

    return credentials.token


def main(argv=None):
    parser = argparse.ArgumentParser(description=(
        'Print a Google ID token for a service account, to exchange at '
        '/service-account/google-sign-in.'))
    parser.add_argument('key_file', help='path to the JSON key file, or - to read it from stdin')
    args = parser.parse_args(argv)

    if args.key_file == '-':
        key = sys.stdin.read()
    else:
        with open(args.key_file, encoding='utf-8') as key_file:
            key = key_file.read()

    try:
        print(mint_credential(key))
    except (ValueError, GoogleAuthError) as e:
        sys.exit(f'Could not mint a credential: {e}')


if __name__ == '__main__':
    main()
