"""Controller functions and routes for authorization CRUD."""

import re

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel, field_validator
from models.Token import Token
from models.Account import Account
from util.enforcer import enforcer, is_authorized

router = APIRouter()

EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class UpdateAuthorizationRequestBody(BaseModel):
    """Request body model."""
    email: str
    add_roles: list[str] = []
    remove_roles: list[str] = []

    @field_validator('email')
    @classmethod
    def validate_email(cls, value):
        if not EMAIL_PATTERN.match(value):
            raise ValueError('email must be a valid email address')
        return value


class PermissionPair(BaseModel):
    """A single (object, action) permission pair."""
    obj: str
    act: str


class UpdateRolePermissionsRequestBody(BaseModel):
    """Request body model."""
    role: str
    add_permissions: list[PermissionPair] = []
    remove_permissions: list[PermissionPair] = []


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

    if not is_authorized(requesting_account.email, role, 'read'):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': f'This account is not authorized to read {role} authorizations.'
        }

    accounts = Account.find_by_role(role)

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

    changed_roles = body.add_roles + body.remove_roles
    is_permitted = all(is_authorized(requesting_account.email, role, 'write') for role in changed_roles)

    if is_permitted:
        for role in body.remove_roles:
            account.remove_role(role)
        for role in body.add_roles:
            account.add_role(role)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': 'This account is not authorized to write to this user\'s authorization(s).'
        }

    account_response = account.__dict__.copy()
    account_response.pop('permissions', None)

    return {
        'account': account_response
    }


@router.get('/role-permissions', tags=['Authorization'])
def get_role_permissions(response: Response,
                         role: str,
                         authorization: str = Header(default=None)):
    """Gets the permissions granted to a role."""

    requesting_account_payload = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account_payload['email'])

    if not is_authorized(requesting_account.email, role, 'read'):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': f'This account is not authorized to read {role} authorizations.'
        }

    permissions = [{'obj': obj, 'act': act} for _, obj, act in enforcer.get_filtered_policy(0, role)]

    return {
        'permissions': permissions
    }


@router.put('/update-role-permissions', tags=['Authorization'])
def update_role_permissions(response: Response,
                            body: UpdateRolePermissionsRequestBody,
                            authorization: str = Header(default=None)):
    """Adds or removes permissions granted to a role."""

    requesting_account_payload = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account_payload['email'])

    if not is_authorized(requesting_account.email, body.role, 'write'):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': f'This account is not authorized to write to the {body.role} role\'s permissions.'
        }

    for permission in body.remove_permissions:
        enforcer.remove_policy(body.role, permission.obj, permission.act)
    for permission in body.add_permissions:
        enforcer.add_policy(body.role, permission.obj, permission.act)

    permissions = [{'obj': obj, 'act': act} for _, obj, act in enforcer.get_filtered_policy(0, body.role)]

    return {
        'permissions': permissions
    }
