"""Controller functions and routes for role and permission management."""

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from models.Token import Token
from util.casbin_enforcer import get_enforcer

router = APIRouter()


class RoleBody(BaseModel):
    read: list[str] = []
    write: list[str] = []
    root: bool = False


class CreateRoleBody(RoleBody):
    name: str


def _role_exists(enforcer, name: str) -> bool:
    return (
        bool(enforcer.get_filtered_policy(0, name)) or
        bool(enforcer.get_filtered_grouping_policy(1, name))
    )


def _build_role_dict(enforcer, name: str) -> dict:
    policies = enforcer.get_filtered_policy(0, name)
    read_targets = []
    write_targets = []
    is_root = False
    for _, obj, act in policies:
        if obj == '*':
            is_root = True
        elif act == 'read':
            read_targets.append(obj)
        elif act == 'write':
            write_targets.append(obj)
    result = {'name': name, 'read': sorted(read_targets), 'write': sorted(write_targets)}
    if is_root:
        result['root'] = True
    return result


def _set_role_policies(enforcer, name: str, read: list, write: list, root: bool):
    enforcer.remove_filtered_policy(0, name)
    if root:
        enforcer.add_policy(name, '*', 'read')
        enforcer.add_policy(name, '*', 'write')
    for target in read:
        enforcer.add_policy(name, target, 'read')
    for target in write:
        enforcer.add_policy(name, target, 'write')


def _require_root(authorization: str, response: Response):
    """Decodes the bearer token and checks for root (wildcard write) access.
    Returns the enforcer on success, or sets 400 and returns None."""
    payload = Token.decode_token(authorization.split(' ')[1])
    enforcer = get_enforcer()
    if not enforcer.enforce(payload['email'], '*', 'write'):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return None
    return enforcer


@router.get('/roles', tags=['Roles'])
def list_roles(response: Response, authorization: str = Header(default=None)):
    """Lists all roles and their permissions. Requires root access."""
    enforcer = _require_root(authorization, response)
    if enforcer is None:
        return {'error': 'Root access required.'}

    from_policies = {sub for sub, _, _ in enforcer.get_policy()}
    from_groupings = {obj for _, obj in enforcer.get_grouping_policy() if obj != '_user'}
    role_names = from_policies | from_groupings
    return {'roles': [_build_role_dict(enforcer, name) for name in sorted(role_names)]}


@router.post('/roles', tags=['Roles'])
def create_role(response: Response, body: CreateRoleBody, authorization: str = Header(default=None)):
    """Creates a new role with the given permissions. Requires root access."""
    enforcer = _require_root(authorization, response)
    if enforcer is None:
        return {'error': 'Root access required.'}

    if _role_exists(enforcer, body.name):
        response.status_code = status.HTTP_409_CONFLICT
        return {'error': f"Role '{body.name}' already exists."}

    _set_role_policies(enforcer, body.name, body.read, body.write, body.root)
    return {'role': _build_role_dict(enforcer, body.name)}


@router.get('/roles/{name}', tags=['Roles'])
def get_role(name: str, response: Response, authorization: str = Header(default=None)):
    """Gets a single role's permissions. Requires root access."""
    enforcer = _require_root(authorization, response)
    if enforcer is None:
        return {'error': 'Root access required.'}

    if not _role_exists(enforcer, name):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'error': f"Role '{name}' not found."}

    return {'role': _build_role_dict(enforcer, name)}


@router.put('/roles/{name}', tags=['Roles'])
def update_role(name: str, response: Response, body: RoleBody, authorization: str = Header(default=None)):
    """Replaces all permissions for a role. Requires root access."""
    enforcer = _require_root(authorization, response)
    if enforcer is None:
        return {'error': 'Root access required.'}

    if not _role_exists(enforcer, name):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'error': f"Role '{name}' not found."}

    _set_role_policies(enforcer, name, body.read, body.write, body.root)
    return {'role': _build_role_dict(enforcer, name)}


@router.delete('/roles/{name}', tags=['Roles'])
def delete_role(name: str, response: Response, authorization: str = Header(default=None)):
    """Deletes a role and unassigns all users from it. Requires root access."""
    enforcer = _require_root(authorization, response)
    if enforcer is None:
        return {'error': 'Root access required.'}

    if not _role_exists(enforcer, name):
        response.status_code = status.HTTP_404_NOT_FOUND
        return {'error': f"Role '{name}' not found."}

    enforcer.remove_filtered_policy(0, name)
    enforcer.remove_filtered_grouping_policy(1, name)
    return {'deleted': name}
