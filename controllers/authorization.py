"""Controller functions and routes for authorization CRUD."""

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from models.Token import Token
from models.Account import Account
from util.casbin_enforcer import get_enforcer, sync_user_roles

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
    authorization. This endpoint can query accounts and return that
    list of accounts.
    """
    requesting_account = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account['email'])

    enforcer = get_enforcer()
    sync_user_roles(enforcer, requesting_account.email, requesting_account.roles)

    if enforcer.enforce(requesting_account.email, role, 'read'):
        accounts = Account.find_by_role(role)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': f'This account is not authorized to read {role} authorizations.'
        }

    return {
        'accounts': accounts
    }


@router.put('/update-account-roles', tags=['Authorization'])
def update_authorization(response: Response,
                         body: UpdateAuthorizationRequestBody,
                         authorization: str = Header(default=None)):
    """Adds or removes roles granted to accounts."""
    requesting_account = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account['email'])

    enforcer = get_enforcer()
    sync_user_roles(enforcer, requesting_account.email, requesting_account.roles)

    account = Account.find_by_email(body.email)

    can_assign_roles = all(enforcer.enforce(requesting_account.email, role, 'write') for role in body.add_roles)
    can_revoke_roles = all(enforcer.enforce(requesting_account.email, role, 'write') for role in body.remove_roles)

    if can_assign_roles and can_revoke_roles:
        for role in body.remove_roles:
            account.remove_role(role)
            enforcer.delete_role_for_user(body.email, role)
        for role in body.add_roles:
            account.add_role(role)
            enforcer.add_role_for_user(body.email, role)
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
