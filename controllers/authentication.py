from fastapi import APIRouter, Header
from pydantic import BaseModel
from models.Token import Token

router = APIRouter()


class TokenRequestBody(BaseModel):
    token: str


@router.post('/google-sign-in', tags=['authentication'])
def google_login(body: TokenRequestBody):
    """Authenticates with Google Identity Services.

    The token, supplied by Google Identity Services, is passed in. Returned is a new token which can be used with the rest of the SAT services.
    """
    try:
        google_info = Token.decode_google_token(body.token)
        user_email = google_info['email']

        new_token = Token.generate_token({'email': user_email})

        return {
            'token': new_token
        }

    except ValueError as e:
        return {
            'message': 'There was an error decoding the Google token.',
            'error': e
        }, 500


@router.post('/login', tags=['authentication'])
def login(authorization: str = Header(default=None)):
    """Returns the payload of the token.

    The token, supplied by this service, is passed in. Returned is the payload that was contained in the token.

    For now, this function is only used to test the service.
    """
    try:
        token = authorization.split(' ')[1]
        payload = Token.decode_token(token)

        return payload

    except ValueError as e:
        return {
            'message': 'There was an error decoding the authentication token.',
            'error': e
        }, 500
