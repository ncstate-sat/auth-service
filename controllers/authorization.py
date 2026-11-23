"""Controller functions and routes for authorization CRUD."""

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel, field_validator
from models.Account import Account, EMAIL_PATTERN
from models.Role import Role
from models.RoleMetadata import RoleMetadata
from util.enforcer import enforcer, is_authorized
from util.requesting_account import decode_authorization_header
from util.reserved_permissions import is_reserved_resource

router = APIRouter()


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


class UpdateRoleInheritanceRequestBody(BaseModel):
    """Request body model."""
    role: str
    add_inherited_roles: list[str] = []
    remove_inherited_roles: list[str] = []


def _reserved_role_error(role):
    return {'error': f'{role} is reserved by the auth service and cannot be used as a role.'}


@router.get('/roles', tags=['Authorization'])
def get_roles(authorization: str = Header(default=None)):
    """Gets the names of all known roles.

    A role is "known" once it has at least one permission or is inherited
    by another role. This only exposes role names, not their permissions,
    which stay gated per-role by /role-permissions.
    """

    # Any authenticated account may list role names.
    decode_authorization_header(authorization)

    return {'roles': Role.find_all_names()}


@router.get('/account', tags=['Authorization'])
def get_account(response: Response,
                email: str,
                authorization: str = Header(default=None)):
    """Gets an account's email, roles, and permissions."""

    requesting_account_payload = decode_authorization_header(authorization)
    requesting_account = Account.find_by_email(requesting_account_payload['email'])

    account = Account.find_by_email(email)

    is_permitted = (
        requesting_account.email == account.email
        or all(is_authorized(requesting_account.email, role, 'read') for role in account.roles)
    )

    if not is_permitted:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': f'This account is not authorized to read {email}\'s authorization(s).'
        }

    return {
        'email': account.email,
        'roles': account.roles,
        'inherited_roles': account.inherited_roles,
        'permissions': account.permissions
    }


@router.get('/role-accounts', tags=['Authorization'])
def get_accounts_with_role(response: Response,
                                    role: str,
                                    authorization: str = Header(default=None)):
    """Gets all accounts with specified roles directly assigned to them.

    It may be necessary to query all accounts with a certain
    role. This endpoint can query by role and return a
    list of accounts that have that role directly assigned. It will only
    return accounts with the role explicitly assigned to that account,
    not implicitly.
    """

    # Get the permissions of the requesting account.
    requesting_account = decode_authorization_header(authorization)
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
    requesting_account_payload = decode_authorization_header(authorization)
    requesting_account = Account.find_by_email(requesting_account_payload['email'])

    reserved_role = next((role for role in body.add_roles if is_reserved_resource(role)), None)
    if reserved_role:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return _reserved_role_error(reserved_role)

    account = Account.find_by_email(body.email)

    changed_roles = body.add_roles + body.remove_roles
    is_permitted = all(
        is_authorized(requesting_account.email, role, 'assign') for role in changed_roles
    )

    if is_permitted:
        for role in body.remove_roles:
            account.remove_role(role)
        for role in body.add_roles:
            account.add_role(role)
        RoleMetadata.delete_for_roles_that_no_longer_exist(body.remove_roles)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': 'This account is not authorized to assign or revoke these role(s).'
        }

    account_response = account.__dict__.copy()
    account_response.pop('permissions', None)
    account_response.pop('inherited_roles', None)

    return {
        'account': account_response
    }


@router.get('/role-permissions', tags=['Authorization'])
def get_role_permissions(response: Response,
                         role: str,
                         authorization: str = Header(default=None)):
    """
    Gets the permissions granted to a role.
    
    It will only return the permissions explicitly assigned to that role,
    not any inherited permissions from inherited roles.
    """

    requesting_account_payload = decode_authorization_header(authorization)
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

    requesting_account_payload = decode_authorization_header(authorization)
    requesting_account = Account.find_by_email(requesting_account_payload['email'])

    if is_reserved_resource(body.role):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return _reserved_role_error(body.role)

    if not is_authorized(requesting_account.email, body.role, 'roleupdate'):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': f'This account is not authorized to update the {body.role} role\'s permissions.'
        }

    for permission in body.remove_permissions:
        enforcer.remove_policy(body.role, permission.obj, permission.act)
    for permission in body.add_permissions:
        enforcer.add_policy(body.role, permission.obj, permission.act)
    RoleMetadata.delete_for_roles_that_no_longer_exist([body.role])

    permissions = [{'obj': obj, 'act': act} for _, obj, act in enforcer.get_filtered_policy(0, body.role)]

    return {
        'permissions': permissions
    }


@router.get('/role-inheritance', tags=['Authorization'])
def get_role_inheritance(response: Response,
                         role: str,
                         authorization: str = Header(default=None)):
    """Gets the roles a role inherits from, and its resulting effective permissions."""

    requesting_account_payload = decode_authorization_header(authorization)
    requesting_account = Account.find_by_email(requesting_account_payload['email'])

    if not is_authorized(requesting_account.email, role, 'read'):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': f'This account is not authorized to read {role} authorizations.'
        }

    inherited_roles = enforcer.get_roles_for_user(role)
    effective_permissions = [
        {'obj': obj, 'act': act}
        for obj, act in {(obj, act) for _, obj, act in enforcer.get_implicit_permissions_for_user(role)}
    ]

    return {
        'inherited_roles': inherited_roles,
        'effective_permissions': effective_permissions
    }


@router.put('/update-role-inheritance', tags=['Authorization'])
def update_role_inheritance(response: Response,
                            body: UpdateRoleInheritanceRequestBody,
                            authorization: str = Header(default=None)):
    """Adds or removes the roles a role inherits from."""

    requesting_account_payload = decode_authorization_header(authorization)
    requesting_account = Account.find_by_email(requesting_account_payload['email'])

    roles_being_linked = [body.role, *body.add_inherited_roles]
    reserved_role = next((role for role in roles_being_linked if is_reserved_resource(role)), None)
    if reserved_role:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return _reserved_role_error(reserved_role)

    if not is_authorized(requesting_account.email, body.role, 'roleupdate'):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': f'This account is not authorized to update the {body.role} role\'s inheritance.'
        }

    for inherited_role in body.add_inherited_roles:
        if inherited_role == body.role or body.role in enforcer.get_implicit_roles_for_user(inherited_role):
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                'error': f'Cannot add {inherited_role} as a inherited role of {body.role}: this would create a cycle.'
            }

    for inherited_role in body.remove_inherited_roles:
        enforcer.remove_grouping_policy(body.role, inherited_role)
    for inherited_role in body.add_inherited_roles:
        enforcer.add_grouping_policy(body.role, inherited_role)
    RoleMetadata.delete_for_roles_that_no_longer_exist([body.role, *body.remove_inherited_roles])

    inherited_roles = enforcer.get_roles_for_user(body.role)

    return {
        'inherited_roles': inherited_roles
    }
