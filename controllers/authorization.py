"""Controller functions and routes for authorization CRUD."""

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from models.Token import Token
from models.Account import Account

router = APIRouter()


class UpdateAuthorizationRequestBody(BaseModel):
    """Request body model."""
    email: str
    add_roles: list[str] = []
    remove_roles: list[str] = []


@router.get('/role-accounts', tags=['Authorization'])
def get_accounts_with_role(response: Response,
                                    role: str,
                                    authorization: str = Header(default=None)):
    """Gets all accounts with specified roles.

    It may be necessary to query all accounts with a certain
    permission. This endpoint can query accounts and return that
    list of accounts.
    """

    # Get the permissions of the requesting account.
    requesting_account = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account['email'])
    
    accounts = Account.find_by_role(role) # TODO: We must first verify that the user is authorized to read this data.

    return {
        'accounts': accounts
    }


@router.put('/update-account-roles', tags=['Authorization'])
def update_authorization(response: Response,
                         body: UpdateAuthorizationRequestBody,
                         authorization: str = Header(default=None)):
    """Adds or removes roles granted to accounts."""

    # Get the permissions of the requesting account.
    requesting_account_payload = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account_payload['email'])

    account = Account.find_by_email(body.email)

    if True: # TODO: We must first verify that this user is authorized to make these changes.
        for role in body.remove_roles:
            account.remove_role(role)
        for role in body.add_roles:
            account.add_role(role)

        account.update()
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': 'This account is not authorized to write to this user\'s authorization(s).'
        }

    account_response = account.__dict__.copy()

    if account_response.get('permissions', False):
        account_response.pop('permissions')

    return {
        'account': account_response
    }
