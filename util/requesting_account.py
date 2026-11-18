"""Reads the account making a request to the auth service from its Authorization header."""

from fastapi import HTTPException
from models.Token import Token


def decode_authorization_header(authorization):
    """Decodes the Bearer token, rejecting anything but a non-impersonation access token.

    Refresh tokens only work at /refresh-token. Impersonation tokens are meant for other
    services, so they can never manage roles, permissions, or further impersonation here.
    """
    payload = Token.decode_token(authorization.split(' ')[1])

    if not Token.is_access(payload):
        raise HTTPException(403, detail='Only access tokens can be used to authorize requests.')

    if Token.is_impersonation(payload):
        raise HTTPException(403,
                            detail='Impersonation tokens cannot be used with the auth service.')

    return payload
