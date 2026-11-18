"""Permissions owned by the auth service itself rather than by any role."""

AUTH_RESOURCE = 'auth'
RESERVED_RESOURCES = [AUTH_RESOURCE]
IMPERSONATE_ACTION = 'impersonate'


def is_reserved_resource(name):
    """Returns whether a role or permission object uses a reserved resource name."""
    return name in RESERVED_RESOURCES
