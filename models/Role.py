"""Roles as casbin sees them. With no role registry, a role exists while casbin references it."""

from models.Account import EMAIL_PATTERN
from util.enforcer import enforcer


class Role:
    """Answers which roles exist, derived live from casbin's policies."""

    @staticmethod
    def find_all_names():
        """Every role with a permission, an account, or an inheritance link, sorted.

        Accounts share casbin's grouping relation with roles, so email addresses are filtered out.
        """
        names = {subject for subject, _, _ in enforcer.get_policy()}
        names.update(enforcer.get_all_roles())
        names.update(subject for subject, _ in enforcer.get_grouping_policy())
        return sorted(name for name in names if not EMAIL_PATTERN.match(name))

    @staticmethod
    def exists(name):
        """Returns whether casbin still references the role."""
        return name in Role.find_all_names()
