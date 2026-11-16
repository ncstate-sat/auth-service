"""Controller functions and routes for impersonating users."""

import logging

from fastapi import APIRouter, Header, Response, status
from models.Account import EMAIL_PATTERN, Account
from models.Token import Token
from pydantic import BaseModel, field_validator
from util.enforcer import is_authorized, is_root_admin
from util.identity import SERVICE_ACCOUNT_EMAIL_PATTERN
from util.requesting_account import decode_authorization_header
from util.reserved_permissions import AUTH_RESOURCE, IMPERSONATE_ACTION

router = APIRouter()
logger = logging.getLogger(__name__)


class ImpersonationRequestBody(BaseModel):
    """Request body model."""
    email: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, value):
        if not EMAIL_PATTERN.match(value):
            raise ValueError('email must be a valid email address')
        return value


def _can_be_impersonated(email):
    return not SERVICE_ACCOUNT_EMAIL_PATTERN.match(email) and not is_root_admin(email)


def _impersonation_token(target_email, impersonator_email):
    account = Account.find_by_email(target_email)
    payload = {**account.__dict__, 'account_type': 'user', 'impersonated_by': impersonator_email}
    return Token.generate_token(payload)


@router.post('/impersonate', tags=['Impersonation'])
def impersonate(response: Response,
                body: ImpersonationRequestBody,
                authorization: str = Header(default=None)):
    """Returns a short-lived auth token for acting as another user.

    Requires the `auth:impersonate` permission. The token's payload is the target user's, plus
    an `impersonated_by` claim with the requester's email. No refresh token is issued, and the
    auth service rejects impersonation tokens on all of its own endpoints. Service accounts and
    the root admin can't be impersonated.
    """
    impersonator_email = decode_authorization_header(authorization)['email']

    if not is_authorized(impersonator_email, AUTH_RESOURCE, IMPERSONATE_ACTION):
        logger.warning('%s was denied impersonating %s: missing permission',
                       impersonator_email, body.email)
        response.status_code = status.HTTP_403_FORBIDDEN
        return {'error': 'This account is not authorized to impersonate users.'}

    if not _can_be_impersonated(body.email):
        logger.warning('%s was denied impersonating %s: protected account',
                       impersonator_email, body.email)
        response.status_code = status.HTTP_403_FORBIDDEN
        return {'error': f'{body.email} cannot be impersonated.'}

    token = _impersonation_token(body.email, impersonator_email)
    logger.info('%s impersonated %s', impersonator_email, body.email)

    return {'token': token}
