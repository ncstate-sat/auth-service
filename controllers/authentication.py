from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from models.Account import Account
from models.Token import Token

router = APIRouter()


class TokenRequestBody(BaseModel):
    token: str


@router.post('/google-sign-in', tags=['Authentication'])
def google_login(response: Response, body: TokenRequestBody):
    """Authenticates with Google Identity Services.

    The token, supplied by Google Identity Services, is passed in. Returned is a new token which can be used with other services.
    """
    try:
        google_info = Token.decode_google_token(body.token)
        user_email = google_info['email']
        account = Account.find_by_email(user_email)

        new_token = Token.generate_token(account.__dict__)
        new_refresh_token = Token.generate_refresh_token(account.email)

        return {
            'token': new_token,
            'refresh_token': new_refresh_token,
            'payload': account.__dict__
        }

    except ValueError as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            'message': 'There was an error decoding the Google token.',
            'error': e
        }


@router.post('/login', tags=['Authentication'])
def login(response: Response, authorization: str = Header(default=None)):
    """Returns the payload of the token.

    The token, supplied by this service, is passed in. Returned is the payload that was contained in the token.

    For now, this function is only used to test the service.
    """
    token = authorization.split(' ')[1]
    payload = Token.decode_token(token)

    return payload

    # except:
    #     response.status_code = status.HTTP_401_UNAUTHORIZED
    #     return {
    #         'message': 'Not Authenticated'
    #     }


@router.post('/refresh-token', tags=['Authentication'])
def refresh_token(response: Response, body: TokenRequestBody):
    """Returns a new token and refresh token.

    The JWT used for authentication expires 15 minutes after it's generated. The refresh token can be used to extend the user's session with the app without asking them to sign back in. This function takes a refresh token, and it returns a new auth token (expires in 15 minutes) and a new refresh token.
    """
    payload = Token.decode_token(body.token)
    account = Account.find_by_email(payload['email'])

    new_token = Token.generate_token(account.__dict__)
    new_refresh_token = Token.generate_refresh_token(account.email)

    return {
        'token': new_token,
        'refresh_token': new_refresh_token,
        'payload': account.__dict__
    }

    # except:
    #     response.status_code = status.HTTP_401_UNAUTHORIZED
    #     return {
    #         'message': 'Refresh Token Expired'
    #     }
