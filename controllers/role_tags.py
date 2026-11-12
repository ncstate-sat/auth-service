"""Controller functions and routes for the tags that can be assigned to roles."""

from fastapi import APIRouter, HTTPException, Response, status
from models.RoleMetadata import RoleMetadata
from models.RoleTag import DuplicateTagError, RoleTag
from pydantic import BaseModel, field_validator

router = APIRouter(prefix='/role-tags', tags=['Role Tags'])


class RoleTagResponse(BaseModel):
    """A tag that can be assigned to roles."""
    name: str


class RoleTagListResponse(BaseModel):
    """Every registered tag."""
    role_tags: list[RoleTagResponse]


class CreateRoleTagRequestBody(BaseModel):
    """Request body model."""
    name: str

    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('name must not be empty')
        return value


@router.get('', response_model=RoleTagListResponse)
def get_all_role_tags():
    """Gets every registered tag, sorted by name."""
    return {'role_tags': RoleTag.find_all()}


@router.post('', response_model=RoleTagResponse, status_code=status.HTTP_201_CREATED,
             responses={status.HTTP_409_CONFLICT: {'description': 'Tag already exists'}})
def create_role_tag(body: CreateRoleTagRequestBody):
    """Registers a tag so it can be assigned to roles. Names are unique, ignoring case."""
    try:
        return RoleTag.create(body.name)
    except DuplicateTagError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error


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
