from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from models.Account import Account
from models.Token import Token
from util.identity import (SERVICE_ACCOUNT_EMAIL_PATTERN, service_account_audiences,
                           verify_google_credential)

router = APIRouter()


class TokenRequestBody(BaseModel):
    token: str


def _user_token_response(account):
    """Issues an auth token and refresh token for a user account."""
    payload = {**account.__dict__, 'account_type': 'user'}

    return {
        'token': Token.generate_token(payload),
        'refresh_token': Token.generate_refresh_token(account.email),
        'payload': payload
    }


@router.post('/google-sign-in', tags=['Authentication'])
def google_login(response: Response, body: TokenRequestBody):
    """Authenticates with Google Identity Services.

    The token, supplied by Google Identity Services, is passed in. Returned is a new token which can be used with other services.

    Google Cloud service accounts can't use this endpoint; they sign in through
    `/service-account/google-sign-in`.
    """
    identity = verify_google_credential(body.token)

    if SERVICE_ACCOUNT_EMAIL_PATTERN.match(identity.email):
        response.status_code = status.HTTP_403_FORBIDDEN
        return {
            'error': 'Service accounts must sign in through /service-account/google-sign-in.'
        }

    return _user_token_response(Account.find_by_email(identity.email))


@router.post('/service-account/google-sign-in', tags=['Authentication'])
def service_account_google_login(response: Response, body: TokenRequestBody):
    """Authenticates a Google Cloud service account.

    The token is a Google-signed ID token minted by the service account itself (for example, with
    `google.oauth2.id_token.fetch_id_token`), with an audience listed in `GOOGLE_SERVICE_AUDIENCES`.

    Like a user, any service account can sign in; what it can do comes from the roles granted to it
    through `/update-account-roles`. Returned is an auth token with `account_type` set to `service`.
    No refresh token is issued; when the auth token expires, the service account mints a new Google
    ID token and signs in again.
    """
    identity = verify_google_credential(body.token, service_account_audiences())

    if not SERVICE_ACCOUNT_EMAIL_PATTERN.match(identity.email):
        response.status_code = status.HTTP_403_FORBIDDEN
        return {
            'error': ('Only Google Cloud service accounts can sign in here. '
                      'Use /google-sign-in instead.')
        }

    account = Account.find_by_email(identity.email)
    payload = {**account.__dict__, 'account_type': 'service'}

    return {
        'token': Token.generate_token(payload),
        'payload': payload
    }


@router.post('/login', tags=['Authentication'])
def login(authorization: str = Header(default=None)):
    """Returns the payload of the token.

    The token, supplied by this service, is passed in. Returned is the payload that was contained in the token.

    For now, this function is only used to test the service.
    """
    token = authorization.split(' ')[1]
    payload = Token.decode_token(token)

    return payload


@router.post('/refresh-token', tags=['Authentication'])
def refresh_token(response: Response, body: TokenRequestBody):
    """Returns a new token and refresh token.

    The JWT used for authentication expires 15 minutes after it's generated. The refresh token can be used to extend the user's session with the app without asking them to sign back in. This function takes a refresh token, and it returns a new auth token (expires in 15 minutes) and a new refresh token.

    Service accounts can't refresh tokens; they sign in again instead.
    """
    payload = Token.decode_token(body.token)

    if SERVICE_ACCOUNT_EMAIL_PATTERN.match(payload['email']):
        response.status_code = status.HTTP_403_FORBIDDEN
        return {
            'error': ('Service accounts can\'t refresh tokens. '
                      'Sign in through /service-account/google-sign-in again.')
        }

    return _user_token_response(Account.find_by_email(payload['email']))
