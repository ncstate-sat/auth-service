"""Fixtures shared across test files."""

import mongomock
import pytest
from models.RoleMetadata import RoleMetadata
from models.RoleTag import RoleTag


@pytest.fixture
def in_memory_role_collections(monkeypatch):
    """Swaps the real role metadata and tag collections for in-memory ones with the real indexes."""
    database = mongomock.MongoClient().auth_service
    monkeypatch.setattr(RoleMetadata, 'collection', database.role_metadata)
    monkeypatch.setattr(RoleTag, 'collection', database.role_tags)
    RoleMetadata.ensure_indexes()
    RoleTag.ensure_indexes()
