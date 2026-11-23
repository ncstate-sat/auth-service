"""Controller functions and routes for role metadata (alias, tags, and description) CRUD."""

from fastapi import APIRouter, Header, HTTPException, Query, Response, status
from models.Account import EMAIL_PATTERN
from models.RoleMetadata import DuplicateAliasError, RoleMetadata, UnknownTagError
from pydantic import BaseModel, ValidationInfo, field_validator, model_validator
from util.enforcer import is_authorized
from util.requesting_account import decode_authorization_header

router = APIRouter(prefix='/role-metadata', tags=['Role Metadata'])

EDITABLE_FIELDS = {'alias', 'tags', 'description'}


class RoleMetadataResponse(BaseModel):
    """A role's metadata. Missing values are null."""
    role: str
    alias: str | None = None
    tags: list[str] = []
    description: str | None = None


class RoleMetadataListResponse(BaseModel):
    """Every role that has metadata."""
    role_metadata: list[RoleMetadataResponse]


class SaveRoleMetadataRequestBody(BaseModel):
    """Request body model.

    Fields left out keep their current value; fields sent as null are cleared.
    Sent tags replace the role's whole tag list, with duplicates removed; [] clears it.
    """
    role: str
    alias: str | None = None
    tags: list[str] | None = None
    description: str | None = None

    @field_validator('role')
    @classmethod
    def validate_role(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('role must not be empty')
        if EMAIL_PATTERN.match(value):
            raise ValueError('role must be a role name, not an email address')
        return value

    @field_validator('alias', 'description')
    @classmethod
    def validate_clearable_text(cls, value, info: ValidationInfo):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError(f'{info.field_name} must not be empty; send null to clear it')
        return value

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, value):
        if value is None:
            return value
        tags = [tag.strip() for tag in value]
        if not all(tags):
            raise ValueError('tags must not be empty; send [] or null to clear them')
        return tags

    @model_validator(mode='after')
    def require_a_change(self):
        if not self.metadata_changes():
            raise ValueError('provide at least one of alias, tags, or description')
        return self

    def metadata_changes(self):
        """The alias, tags, and description values the request actually sent, including nulls."""
        return {field: getattr(self, field) for field in self.model_fields_set & EDITABLE_FIELDS}


def _require_permission_on_role(authorization, role, action, denied_message):
    requesting_email = decode_authorization_header(authorization)['email']
    if not is_authorized(requesting_email, role, action):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=denied_message)


def _require_role_read_permission(authorization, role):
    _require_permission_on_role(
        authorization, role, 'read',
        f'This account is not authorized to read the {role} role\'s metadata.')


def _require_role_update_permission(authorization, role):
    _require_permission_on_role(
        authorization, role, 'roleupdate',
        f'This account is not authorized to update the {role} role\'s metadata.')


@router.get('', response_model=RoleMetadataListResponse)
def get_all_role_metadata(
        tag: str | None = Query(None, description='Only include roles with this tag'),
        authorization: str = Header(default=None)):
    """Gets the metadata of every role the requester can read (`<role>:read`) that has some."""
    requesting_email = decode_authorization_header(authorization)['email']
    readable_metadata = [metadata for metadata in RoleMetadata.find_all(tag)
                         if is_authorized(requesting_email, metadata['role'], 'read')]
    return {'role_metadata': readable_metadata}


@router.get('/{role:path}', response_model=RoleMetadataResponse,
            responses={status.HTTP_403_FORBIDDEN: {
                'description': 'Missing <role>:read permission'}})
def get_role_metadata(role: str, authorization: str = Header(default=None)):
    """Gets one role's metadata. Requires `<role>:read`. Returns 404 if the role has none."""
    _require_role_read_permission(authorization, role)
    metadata = RoleMetadata.find_by_role(role)
    if metadata is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f'Role "{role}" has no metadata.')
    return metadata


@router.post('', response_model=RoleMetadataResponse,
             responses={status.HTTP_201_CREATED: {'description': 'Metadata created'},
                        status.HTTP_403_FORBIDDEN: {
                            'description': 'Missing <role>:roleupdate permission'},
                        status.HTTP_409_CONFLICT: {'description': 'Alias already in use'},
                        status.HTTP_422_UNPROCESSABLE_CONTENT: {
                            'description': 'Invalid body or unregistered tag'}})
def save_role_metadata(body: SaveRoleMetadataRequestBody, response: Response,
                       authorization: str = Header(default=None)):
    """Creates a role's metadata, or updates it if the role already has some.

    Requires `<role>:roleupdate`. Returns 201 when created and 200 when updated. Aliases are
    unique across roles, ignoring case. Tags must already be registered at /role-tags.
    """
    _require_role_update_permission(authorization, body.role)

    try:
        metadata, was_created = RoleMetadata.save(body.role, body.metadata_changes())
    except DuplicateAliasError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    except UnknownTagError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    response.status_code = status.HTTP_201_CREATED if was_created else status.HTTP_200_OK
    return metadata


@router.delete('/{role:path}', status_code=status.HTTP_204_NO_CONTENT,
               responses={status.HTTP_403_FORBIDDEN: {
                   'description': 'Missing <role>:roleupdate permission'}})
def delete_role_metadata(role: str, authorization: str = Header(default=None)):
    """Deletes a role's metadata. Requires `<role>:roleupdate`. Casbin data is untouched."""
    _require_role_update_permission(authorization, role)
    if not RoleMetadata.delete(role):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f'Role "{role}" has no metadata.')
    return Response(status_code=status.HTTP_204_NO_CONTENT)
