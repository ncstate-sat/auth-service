"""Verifies credentials from external identity providers.

Each provider's credential is normalized into an Identity, so the
controllers don't depend on any one provider's token format. Only Google
is supported today; Entra ID is expected to be added as another verifier.
"""

import re
from dataclasses import dataclass

from fastapi import HTTPException
from google.auth.exceptions import GoogleAuthError
from models.Token import Token

# Google Cloud service accounts always have an address in this domain.
SERVICE_ACCOUNT_EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.iam\.gserviceaccount\.com$')


@dataclass(frozen=True)
class Identity:
    """A verified identity from an external provider."""
    provider: str   # The identity provider, e.g. 'google'.
    subject: str    # The provider's stable, unique ID for the identity.
    email: str      # The identity's verified email address.


def verify_google_credential(token):
    """Verifies a Google-signed ID token and returns its Identity.

    Raises HTTPException(401) if the token is invalid, expired, issued for a
    different audience, or doesn't carry a verified email address.
    """
    try:
        google_info = Token.decode_google_token(token)
    except (ValueError, GoogleAuthError) as e:
        raise HTTPException(401, detail=f'The Google credential could not be verified: {e}')

    if not google_info.get('email') or not google_info.get('email_verified'):
        raise HTTPException(401, detail=('The Google credential does not contain '
                                         'a verified email address.'))

    return Identity(provider='google', subject=google_info['sub'], email=google_info['email'])
