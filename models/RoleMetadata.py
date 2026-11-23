"""A model to handle role metadata CRUD, stored apart from casbin's policy data."""

from models.Role import Role
from models.RoleTag import RoleTag
from pymongo.errors import DuplicateKeyError
from util.database import database

PUBLIC_FIELDS = {'_id': False, 'role': True, 'alias': True, 'tags': True, 'description': True}


class DuplicateAliasError(Exception):
    """Raised when an alias is already used by a different role."""

    def __init__(self, alias, owning_role=None):
        self.alias = alias
        self.owning_role = owning_role
        owner = f' by role "{owning_role}"' if owning_role else ''
        super().__init__(f'The alias "{alias}" is already used{owner}.')


class UnknownRoleError(Exception):
    """Raised when metadata is saved for a role that doesn't exist in casbin."""

    def __init__(self, role):
        self.role = role
        super().__init__(
            f'Role "{role}" does not exist. Give it a permission, an account, or an '
            'inheritance link first.')


class UnknownTagError(Exception):
    """Raised when a role is given tags that aren't registered."""

    def __init__(self, unknown_tags):
        self.unknown_tags = unknown_tags
        quoted = ', '.join(f'"{tag}"' for tag in unknown_tags)
        super().__init__(
            f'These tags are not registered: {quoted}. Create them at /role-tags first.')


class RoleMetadata:
    """The RoleMetadata model handles CRUD for a role's alias, tags, and description.

    A role does not need metadata, but metadata needs its role: it can only be
    saved for a role casbin references, and is deleted once casbin no longer does.
    """
    collection = database['role_metadata']

    @classmethod
    def ensure_indexes(cls):
        """Creates the indexes that keep roles and aliases unique."""
        cls.collection.create_index('role', unique=True)
        # alias_key is only present while a role has an alias, so the sparse
        # index lets any number of roles go without one.
        cls.collection.create_index('alias_key', unique=True, sparse=True)
        cls.collection.create_index('tags')

    @classmethod
    def find_all(cls, tag=None):
        """Finds the metadata of every role that has some, sorted by role name.

        When a tag is given, only roles with that tag are included.
        """
        query = {} if tag is None else {'tags': tag}
        return [
            _with_missing_fields(document)
            for document in cls.collection.find(query, PUBLIC_FIELDS).sort('role')
        ]

    @classmethod
    def find_roles_with_tag(cls, tag):
        """Finds the names of every role that has the tag, sorted."""
        return [document['role'] for document in
                cls.collection.find({'tags': tag}, {'role': True}).sort('role')]

    @classmethod
    def find_by_role(cls, role):
        """Finds a role's metadata, or None if the role has none."""
        document = cls.collection.find_one({'role': role}, PUBLIC_FIELDS)
        return _with_missing_fields(document) if document else None

    @classmethod
    def save(cls, role, changes):
        """Creates or updates a role's metadata and returns (metadata, was_created).

        changes maps any of 'alias', 'tags', and 'description' to a new value;
        None clears that field and a field left out of changes keeps its current
        value. The role must exist in casbin, and tags must already be registered as RoleTags.
        """
        if not Role.exists(role):
            raise UnknownRoleError(role)
        if changes.get('alias') is not None:
            cls._reject_alias_used_by_other_role(role, changes['alias'])
        if changes.get('tags'):
            _reject_unregistered_tags(changes['tags'])

        try:
            result = cls.collection.update_one(
                {'role': role}, _build_update(changes), upsert=True)
        except DuplicateKeyError as error:
            raise DuplicateAliasError(changes.get('alias')) from error

        return cls.find_by_role(role), result.upserted_id is not None

    @classmethod
    def delete(cls, role):
        """Deletes a role's metadata. Returns whether there was any to delete."""
        return cls.collection.delete_one({'role': role}).deleted_count == 1

    @classmethod
    def delete_for_roles_that_no_longer_exist(cls, roles):
        """Deletes the metadata of any of the given roles that casbin no longer references."""
        for role in set(roles):
            if not Role.exists(role):
                cls.delete(role)

    @classmethod
    def _reject_alias_used_by_other_role(cls, role, alias):
        owner = cls.collection.find_one(
            {'alias_key': _alias_key(alias), 'role': {'$ne': role}}, {'role': True})
        if owner:
            raise DuplicateAliasError(alias, owner['role'])


def _reject_unregistered_tags(tags):
    unregistered = RoleTag.find_unregistered(tags)
    if unregistered:
        raise UnknownTagError(unregistered)


def _alias_key(alias):
    """Aliases that differ only by case count as the same alias."""
    return alias.casefold()


def _build_update(changes):
    stored_fields = _stored_fields_for(changes)
    fields_to_set = {field: value for field, value in stored_fields.items() if value is not None}
    fields_to_unset = {field: '' for field, value in stored_fields.items() if value is None}

    update = {}
    if fields_to_set:
        update['$set'] = fields_to_set
    if fields_to_unset:
        update['$unset'] = fields_to_unset
    return update


def _stored_fields_for(changes):
    """Maps the requested changes to the document fields they set, with None meaning unset."""
    stored_fields = {}
    if 'alias' in changes:
        alias = changes['alias']
        stored_fields['alias'] = alias
        stored_fields['alias_key'] = None if alias is None else _alias_key(alias)
    if 'tags' in changes:
        tags = changes['tags']
        stored_fields['tags'] = list(dict.fromkeys(tags)) if tags else None
    if 'description' in changes:
        stored_fields['description'] = changes['description']
    return stored_fields


def _with_missing_fields(document):
    return {'alias': None, 'tags': [], 'description': None, **document}
