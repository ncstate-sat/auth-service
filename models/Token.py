import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests as google_auth_requests


TOKEN_EXP_TIME = timedelta(minutes=15)
REFRESH_TOKEN_EXP_TIME = timedelta(days=2)
ACCESS_TOKEN_TYPE = 'access'
REFRESH_TOKEN_TYPE = 'refresh'

class Token:
    @staticmethod
    def decode_google_token(token):
        """Decodes a token from Google Identity Services.
        :param token: The token from Google.
        """
        return id_token.verify_oauth2_token(token, google_auth_requests.Request(),
                                            os.getenv('GOOGLE_CLIENT_ID'))

    @staticmethod
    def decode_token(token):
        """Decodes a JSON Web Token from this Auth Service.
        :param token: The token from this service.
        """
        try:
            return jwt.decode(token, os.getenv('JWT_SECRET'), ['HS256'])
        except jwt.exceptions.ExpiredSignatureError:
            raise HTTPException(401, detail="Token is expired")
        except jwt.exceptions.InvalidSignatureError:
            raise HTTPException(400, detail=("Token has an invalid signature. "
                                             "Check the JWT_SECRET variable."))

    @staticmethod
    def generate_token(payload):
        """Generates a JSON Web Token given a payload.
        :param payload: The object which will be encoded in the token.
        """
        token_payload = {
            'exp': datetime.now(tz=timezone.utc) + TOKEN_EXP_TIME,
            **payload,
            'token_type': ACCESS_TOKEN_TYPE,
        }

        return jwt.encode(token_payload, os.getenv('JWT_SECRET'), 'HS256')

    @staticmethod
    def generate_refresh_token(email):
        """Generates a refresh JWT given an email address.
        :param email: The email address of the user, which will be encoded in the token.
        """
        token_payload = {'email': email, 'token_type': REFRESH_TOKEN_TYPE,
                           'exp': datetime.now(tz=timezone.utc) + REFRESH_TOKEN_EXP_TIME}

        return jwt.encode(token_payload, os.getenv('JWT_SECRET'), 'HS256')

    @staticmethod
    def is_access(payload):
        """Returns whether a decoded payload came from an access token."""
        return payload.get('token_type') == ACCESS_TOKEN_TYPE

    @staticmethod
    def is_refresh(payload):
        """Returns whether a decoded payload came from a refresh token."""
        return payload.get('token_type') == REFRESH_TOKEN_TYPE

    @staticmethod
    def is_impersonation(payload):
        """Returns whether a decoded payload came from an impersonation token."""
        return 'impersonated_by' in payload

    @classmethod
    def decode_refresh_token(cls, token):
        """Decodes a refresh JWT from this Auth Service.
        :param token: The refresh token from this service.
        """
        return cls.decode_token(token)
