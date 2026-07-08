# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this service does

A FastAPI service that handles authentication (Google Sign-In → JWT) and authorization (Casbin-based RBAC with role inheritance) for other services. It issues its own JWTs after verifying a Google Identity Services token, and those JWTs carry the user's email, roles, and a flattened list of `resource:action` permissions so downstream services don't need to call back into this one to check access.

## Commands

```bash
make setup          # install pip-tools, then pip-sync base + dev requirements into the active venv
make run-dev         # uvicorn main:app --reload --port 8000
make update-requirements  # regenerate requirements/base/base.txt and requirements/dev/dev.txt from pyproject.toml
```

Testing:
```bash
pytest                                    # run all tests
pytest tests/test_authorization.py        # run one file
pytest tests/test_authorization.py::test_add_role  # run one test
```

Docker (app + Mongo):
```bash
docker compose up -d --build
docker compose down
docker exec -it auth-service sh   # then run pytest inside the container
```

Required env vars (see `sample_envrc` / README): `GOOGLE_CLIENT_ID`, `JWT_SECRET`, `MONGODB_URL`, optional `ROOT_ADMIN_EMAIL`. Tests set `JWT_SECRET` inline and monkeypatch the Casbin enforcer, so they don't need a real Mongo instance or Google credentials.

There is no separate lint/typecheck make target, but `ruff`, `black`, `mypy`, and `bandit` are in the dev dependencies (`pyproject.toml`) and configured there — run them directly (e.g. `ruff check .`, `mypy .`) if asked to lint/typecheck.

## Architecture

**Request flow:** `main.py` wires up FastAPI and mounts two routers — `controllers/authentication.py` (`/google-sign-in`, `/login`, `/refresh-token`) and `controllers/authorization.py` (role/permission CRUD). Controllers are thin: decode the token, check authorization via `util/enforcer.py`, then delegate to `models/`.

**Casbin is the source of truth for roles/permissions**, not a bolt-on. There is no separate "roles" collection — `models/Account.py`'s `roles` and `permissions` are always derived live from the Casbin enforcer (`get_roles_for_user`, `get_implicit_permissions_for_user`), never stored on an Account document. An "account" only exists implicitly, as a subject with grouping-policy edges in Casbin.

- `util/model.conf` defines the Casbin model: RBAC with a single grouping relation `g = _, _` used for **both** "account has role" and "role inherits role" — accounts and roles share the same node space. This is why `Account.find_by_role` (`models/Account.py`) has to filter results through `EMAIL_PATTERN` to exclude other roles that inherit from the queried role.
- `util/enforcer.py` creates the global `enforcer` (backed by `casbin_pymongo_adapter` against the `auth_service` Mongo database) and exposes `is_authorized(sub, obj, act)`, which wraps `enforcer.enforce` with a standing bypass for `ROOT_ADMIN_EMAIL`. This bypass exists solely to bootstrap the first role/permission on a fresh system where no Casbin policy grants anyone access yet (see README's "Bootstrapping the First Admin"). Almost all authorization checks in controllers should go through `is_authorized`, not `enforcer.enforce` directly.
- Permissions are `(role, obj, act)` triples (a "policy"); role inheritance is a `(role, inherited_role)` grouping policy. `update-role-inheritance` explicitly rejects cycles (self and transitive) before calling `add_grouping_policy` — see `controllers/authorization.py`.
- A role is considered "known" (surfaced by `GET /roles`) if it appears as a policy subject or anywhere in `get_all_roles()`; there's no independent role registry.

**Tokens** (`models/Token.py`): auth JWTs expire in 15 minutes, refresh tokens in 2 days, both HS256-signed with `JWT_SECRET`. `decode_token` translates expired/invalid-signature JWT errors into `HTTPException(401)` / `HTTPException(400)` respectively — controllers rely on this rather than catching JWT errors themselves.

**Testing pattern:** tests use FastAPI's `TestClient` against the real `app` and monkeypatch methods directly on the shared `enforcer` singleton (e.g. `monkeypatch.setattr(enforcer, 'enforce', ...)`) rather than mocking at the HTTP layer. `tests/test_authorization.py` is the largest file and a good reference for this pattern, including the `mock_enforce_by_role` helper for stubbing `enforce` by role name.

**Demo website** (`demo-website/`): a static, framework-free JS site exercising the API end-to-end (Google Identity Services sign-in, role/account management UI). Must be served over the same port registered as an authorized origin in Google Cloud Console (see README), and needs the `GOOGLE_CLIENT_ID` hardcoded into `main.js` before use. Not part of the Python app or its test suite.

## Accessibility

Per org policy, any UI work (including changes to `demo-website/`) must meet WCAG 2.1/2.2 AA at minimum — check color contrast, keyboard operability, semantic HTML/ARIA, and focus management before considering front-end changes complete.
