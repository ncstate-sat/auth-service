"""A model to handle role metadata CRUD, stored apart from casbin's policy data."""

from models.RoleTag import RoleTag
from pymongo.errors import DuplicateKeyError
from util.database import database

PUBLIC_FIELDS = {'_id': False, 'role': True, 'alias': True, 'tags': True}


class DuplicateAliasError(Exception):
    """Raised when an alias is already used by a different role."""

    def __init__(self, alias, owning_role=None):
        self.alias = alias
        self.owning_role = owning_role
        owner = f' by role "{owning_role}"' if owning_role else ''
        super().__init__(f'The alias "{alias}" is already used{owner}.')


class UnknownTagError(Exception):
    """Raised when a role is given tags that aren't registered."""

    def __init__(self, unknown_tags):
        self.unknown_tags = unknown_tags
        quoted = ', '.join(f'"{tag}"' for tag in unknown_tags)
        super().__init__(
            f'These tags are not registered: {quoted}. Create them at /role-tags first.')


class RoleMetadata:
    """The RoleMetadata model handles CRUD for a role's alias and tags.

    A role does not need metadata to exist, and metadata does not need the
    role to exist in casbin.
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

        changes maps 'alias' and/or 'tags' to a new value; None clears that field
        and a field left out of changes keeps its current value. Tags must
        already be registered as RoleTags.
        """
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
    fields_to_set = {}
    fields_to_unset = {}

    if 'alias' in changes:
        alias = changes['alias']
        if alias is None:
            fields_to_unset.update({'alias': '', 'alias_key': ''})
        else:
            fields_to_set.update({'alias': alias, 'alias_key': _alias_key(alias)})

    if 'tags' in changes:
        tags = changes['tags']
        if tags:
            fields_to_set['tags'] = list(dict.fromkeys(tags))
        else:
            fields_to_unset['tags'] = ''

    update = {}
    if fields_to_set:
        update['$set'] = fields_to_set
    if fields_to_unset:
        update['$unset'] = fields_to_unset
    return update


def _with_missing_fields(document):
    return {'alias': None, 'tags': [], **document}
