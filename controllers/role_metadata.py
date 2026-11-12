"""Controller functions and routes for role metadata (alias and tags) CRUD."""

from fastapi import APIRouter, HTTPException, Query, Response, status
from models.Account import EMAIL_PATTERN
from models.RoleMetadata import DuplicateAliasError, RoleMetadata, UnknownTagError
from pydantic import BaseModel, field_validator, model_validator

router = APIRouter(prefix='/role-metadata', tags=['Role Metadata'])

EDITABLE_FIELDS = {'alias', 'tags'}


class RoleMetadataResponse(BaseModel):
    """A role's metadata. Missing values are null."""
    role: str
    alias: str | None = None
    tags: list[str] = []


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

    @field_validator('role')
    @classmethod
    def validate_role(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('role must not be empty')
        if EMAIL_PATTERN.match(value):
            raise ValueError('role must be a role name, not an email address')
        return value

    @field_validator('alias')
    @classmethod
    def validate_alias(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError('alias must not be empty; send null to clear it')
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
            raise ValueError('provide an alias, tags, or both')
        return self

    def metadata_changes(self):
        """The alias/tags values the request actually sent, including nulls."""
        return {field: getattr(self, field) for field in self.model_fields_set & EDITABLE_FIELDS}


@router.get('', response_model=RoleMetadataListResponse)
def get_all_role_metadata(
        tag: str | None = Query(None, description='Only include roles with this tag')):
    """Gets the metadata of every role that has some. Roles without metadata are left out."""
    return {'role_metadata': RoleMetadata.find_all(tag)}


@router.get('/{role:path}', response_model=RoleMetadataResponse)
def get_role_metadata(role: str):
    """Gets one role's metadata. Returns 404 if the role has none."""
    metadata = RoleMetadata.find_by_role(role)
    if metadata is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f'Role "{role}" has no metadata.')
    return metadata


@router.post('', response_model=RoleMetadataResponse,
             responses={status.HTTP_201_CREATED: {'description': 'Metadata created'},
                        status.HTTP_409_CONFLICT: {'description': 'Alias already in use'},
                        status.HTTP_422_UNPROCESSABLE_CONTENT: {
                            'description': 'Invalid body or unregistered tag'}})
def save_role_metadata(body: SaveRoleMetadataRequestBody, response: Response):
    """Creates a role's metadata, or updates it if the role already has some.

    Returns 201 when created and 200 when updated. Aliases are unique across
    roles, ignoring case. Tags must already be registered at /role-tags.
    """
    try:
        metadata, was_created = RoleMetadata.save(body.role, body.metadata_changes())
    except DuplicateAliasError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    except UnknownTagError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    response.status_code = status.HTTP_201_CREATED if was_created else status.HTTP_200_OK
    return metadata


@router.delete('/{role:path}', status_code=status.HTTP_204_NO_CONTENT)
def delete_role_metadata(role: str):
    """Deletes a role's metadata. The role itself and its casbin data are untouched."""
    if not RoleMetadata.delete(role):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f'Role "{role}" has no metadata.')
    return Response(status_code=status.HTTP_204_NO_CONTENT)
