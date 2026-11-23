"""Fixtures shared across test files."""

import casbin
import mongomock
import pytest
from models.RoleMetadata import RoleMetadata
from models.RoleTag import RoleTag
from util.enforcer import MODEL_PATH, enforcer

DELEGATED_CASBIN_METHODS = (
    'enforce', 'get_policy', 'get_grouping_policy', 'get_all_roles', 'get_filtered_policy',
    'add_policy', 'remove_policy', 'add_grouping_policy', 'remove_grouping_policy',
    'get_roles_for_user', 'get_users_for_role', 'get_implicit_roles_for_user',
    'get_implicit_permissions_for_user',
)


@pytest.fixture
def in_memory_role_collections(monkeypatch):
    """Swaps the real role metadata and tag collections for in-memory ones with the real indexes."""
    database = mongomock.MongoClient().auth_service
    monkeypatch.setattr(RoleMetadata, 'collection', database.role_metadata)
    monkeypatch.setattr(RoleTag, 'collection', database.role_tags)
    RoleMetadata.ensure_indexes()
    RoleTag.ensure_indexes()


@pytest.fixture
def in_memory_casbin(monkeypatch):
    """Points the shared enforcer at a fresh in-memory one with the real model, and returns it."""
    memory_enforcer = casbin.Enforcer(MODEL_PATH)
    for method in DELEGATED_CASBIN_METHODS:
        monkeypatch.setattr(enforcer, method, getattr(memory_enforcer, method))
    return memory_enforcer
