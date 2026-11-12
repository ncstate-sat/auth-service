"""A model to handle the registry of tags that can be assigned to roles."""

from pymongo.errors import DuplicateKeyError
from util.database import database

PUBLIC_FIELDS = {'_id': False, 'name': True}


class DuplicateTagError(Exception):
    """Raised when a tag name is already registered, ignoring case."""

    def __init__(self, name, existing_name=None):
        self.name = name
        self.existing_name = existing_name
        existing = f' as "{existing_name}"' if existing_name and existing_name != name else ''
        super().__init__(f'The tag "{name}" already exists{existing}.')


class RoleTag:
    """The RoleTag model handles CRUD for the tags consumers define for roles.

    Which tags exist is entirely up to consumers of this service; a role's
    metadata may only reference tags registered here.
    """
    collection = database['role_tags']

    @classmethod
    def ensure_indexes(cls):
        """Creates the index that keeps tag names unique, ignoring case."""
        cls.collection.create_index('name_key', unique=True)

    @classmethod
    def find_all(cls):
        """Finds every tag, sorted by name."""
        return list(cls.collection.find({}, PUBLIC_FIELDS).sort('name'))

    @classmethod
    def exists(cls, name):
        """Whether a tag with exactly this name is registered."""
        return cls.collection.count_documents({'name': name}, limit=1) == 1

    @classmethod
    def find_unregistered(cls, names):
        """Returns the names, in their given order, that aren't registered tags."""
        registered = {
            document['name']
            for document in cls.collection.find({'name': {'$in': list(names)}}, PUBLIC_FIELDS)
        }
        return [name for name in names if name not in registered]

    @classmethod
    def create(cls, name):
        """Registers a new tag and returns it."""
        cls._reject_name_differing_only_by_case(name)
        try:
            cls.collection.insert_one({'name': name, 'name_key': _name_key(name)})
        except DuplicateKeyError as error:
            raise DuplicateTagError(name) from error
        return {'name': name}

    @classmethod
    def delete(cls, name):
        """Deletes a tag. Returns whether there was one to delete."""
        return cls.collection.delete_one({'name': name}).deleted_count == 1

    @classmethod
    def _reject_name_differing_only_by_case(cls, name):
        existing = cls.collection.find_one({'name_key': _name_key(name)}, PUBLIC_FIELDS)
        if existing:
            raise DuplicateTagError(name, existing['name'])


def _name_key(name):
    """Tag names that differ only by case count as the same tag."""
    return name.casefold()
