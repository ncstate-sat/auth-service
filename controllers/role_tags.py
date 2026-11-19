"""Controller functions and routes for the tags that can be assigned to roles."""

from fastapi import APIRouter, HTTPException, Response, status
from models.RoleMetadata import RoleMetadata
from models.RoleTag import DuplicateTagError, RoleTag
from pydantic import BaseModel, field_validator, model_validator

router = APIRouter(prefix='/role-tags', tags=['Role Tags'])


class RoleTagResponse(BaseModel):
    """A tag that can be assigned to roles."""
    name: str
    description: str | None = None


class RoleTagListResponse(BaseModel):
    """Every registered tag."""
    role_tags: list[RoleTagResponse]


def _trimmed_description(value):
    if value is None:
        return value
    value = value.strip()
    if not value:
        raise ValueError('description must not be empty; send null for no description')
    return value


class CreateRoleTagRequestBody(BaseModel):
    """Request body model."""
    name: str
    description: str | None = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('name must not be empty')
        return value

    @field_validator('description')
    @classmethod
    def validate_description(cls, value):
        return _trimmed_description(value)


class UpdateRoleTagRequestBody(BaseModel):
    """Request body model. Send description as null to clear it."""
    description: str | None = None

    @field_validator('description')
    @classmethod
    def validate_description(cls, value):
        return _trimmed_description(value)

    @model_validator(mode='after')
    def require_description(self):
        if 'description' not in self.model_fields_set:
            raise ValueError('provide a description, or null to clear it')
        return self


@router.get('', response_model=RoleTagListResponse)
def get_all_role_tags():
    """Gets every registered tag, sorted by name."""
    return {'role_tags': RoleTag.find_all()}


@router.post('', response_model=RoleTagResponse, status_code=status.HTTP_201_CREATED,
             responses={status.HTTP_409_CONFLICT: {'description': 'Tag already exists'}})
def create_role_tag(body: CreateRoleTagRequestBody):
    """Registers a tag so it can be assigned to roles. Names are unique, ignoring case."""
    try:
        return RoleTag.create(body.name, body.description)
    except DuplicateTagError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.patch('/{name:path}', response_model=RoleTagResponse)
def update_role_tag(name: str, body: UpdateRoleTagRequestBody):
    """Updates a tag's description. Names can't be changed; the name must match exactly."""
    tag = RoleTag.update_description(name, body.description)
    if tag is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f'Tag "{name}" does not exist.')
    return tag


@router.delete('/{name:path}', status_code=status.HTTP_204_NO_CONTENT,
               responses={status.HTTP_409_CONFLICT: {'description': 'Tag is assigned to roles'}})
def delete_role_tag(name: str):
    """Deletes a tag. Rejected with 409 while any role still has the tag."""
    if not RoleTag.exists(name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f'Tag "{name}" does not exist.')

    roles_with_tag = RoleMetadata.find_roles_with_tag(name)
    if roles_with_tag:
        raise HTTPException(status.HTTP_409_CONFLICT, detail={
            'message': f'Tag "{name}" is still assigned to roles. Remove it from them first.',
            'roles': roles_with_tag,
        })

    RoleTag.delete(name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
