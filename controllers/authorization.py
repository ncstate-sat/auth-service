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
    """Gets all accounts with specified authorizations.

    It may be necessary to query all accounts with a certain
    authorization. This endpoint can query accounts and return that
    list of accounts.
    """

    # Get read permissions of the requesting account.
    requesting_account = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account['email'])
    read_permissions: dict = requesting_account.authorizations.get('_read', [])

    # If requesting user has permission, return accounts data.
    if role in read_permissions:
        accounts = Account.find_by_role(role)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': 'This account is not authorized to write to this user\'s authorization(s).'
        }

    return {
        'accounts': accounts
    }


@router.put('/update-account-roles', tags=['Authorization'])
def update_authorization(response: Response,
                         body: UpdateAuthorizationRequestBody,
                         authorization: str = Header(default=None)):
    """Updates the authorization for a user for a given app.

    Apps can store data under each account regarding authorization.
    Apps can pass a dictionary to this endpoint which will be stored in
    the user's account. If no record exists for the app ID, a new
    record will be created. If a record already exists, it will be
    replaced with the new data.
    """

    # Get write permissions of the requesting account.
    requesting_account = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account['email'])
    write_permissions: dict = requesting_account.authorizations.get('_write', [])

    account = Account.find_by_email(body.email)

    # Verify that the requesting account has permission to assign this role.
    can_assign_roles: bool = all(role in write_permissions for role in body.add_roles)
    can_revoke_roles: bool = all(role in write_permissions for role in body.remove_roles)

    if can_assign_roles and can_revoke_roles:
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

    if account_response.get('authorizations', False):
        account_response.pop('authorizations')

    return {
        'account': account_response
    }
