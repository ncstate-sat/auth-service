import os
import jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_auth_requests


class Token:
    @staticmethod
    def decode_google_token(token):
        """Decodes a token from Google Identity Services.
        :param token: The token from Google.
        """
        return id_token.verify_oauth2_token(token, google_auth_requests.Request(), os.getenv('GOOGLE_CLIENT_ID'))

    @staticmethod
    def decode_token(token):
        """Decodes a JSON Web Token from this Auth Service.
        :param token: The token from this service.
        """
        return jwt.decode(token, os.getenv('JWT_SECRET'), ['HS256'])

    @staticmethod
    def generate_token(payload):
        """Generates a JSON Web Token given a payload.
        :param payload: The object which will be encoded in the token.
        """
        return jwt.encode(payload, os.getenv('JWT_SECRET'), 'HS256')
