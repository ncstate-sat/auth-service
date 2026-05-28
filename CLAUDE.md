# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (with hot reload)
uvicorn main:app --reload

# Run all tests
pytest

# Run a single test
pytest tests/test_authentication.py::test_decode_token

# Build and run in Docker
docker build -t auth-service .
docker run -p 8000:8000 --env-file .env auth-service
```

## Required Environment Variables

| Variable           | Description                                                      |
| ------------------ | ---------------------------------------------------------------- |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console; used to verify Google Identity tokens |
| `JWT_SECRET`       | Shared secret for signing/verifying JWTs across services         |
| `MONGODB_URL`      | MongoDB connection string                                        |

For local development: `docker run -p 27017:27017 --name auth-db -d mongo`

## Architecture

**FastAPI** app (`main.py`) with two routers and a MongoDB backend.

### Request Flow

1. Client sends a Google Identity token to `POST /google-sign-in`
2. `Token.decode_google_token()` validates it with Google's API
3. `Account.find_by_email()` looks up (or auto-creates) the account in MongoDB
4. Service returns a short-lived **auth token** (15 min) and a **refresh token** (2 days)
5. When the auth token expires, `POST /refresh-token` issues new tokens using the refresh token

### Layer Responsibilities

- **`controllers/`** — Route handlers; parse requests, delegate to models, return responses
- **`models/Account.py`** — Account business logic and CRUD; delegates all DB calls to `AuthDB`
- **`models/Token.py`** — JWT encode/decode (auth and refresh), Google token verification
- **`util/db.py`** — `AuthDB` class; all MongoDB queries live here. Collections are lazily initialized on first use.

### Authorization Model

Roles are stored in the `roles` MongoDB collection and assigned to users in the `accounts` collection. When an account is loaded, `AuthDB.get_account_by_email()` aggregates authorizations from all of the user's roles into a single flat dict. Two protected keys control RBAC within this service:

- `_read`: list of role names the bearer can query via `GET /role-accounts`
- `_write`: list of role names the bearer can assign/revoke via `PUT /update-account-roles`
- `root: true`: bypasses all `_read`/`_write` restrictions

Authorizations are embedded in the JWT payload, so downstream services can enforce them without hitting the database.

### Testing

Tests use `pytest` with `fastapi.testclient.TestClient`. Database calls are monkeypatched at the `AuthDB` layer. Tests set `os.environ["JWT_SECRET"]` directly — no `.env` file needed to run them.

## Future Work

### Using Casbin

Right now, the application manages roles and permissions on its own, and its stored in a MongoDB database. Each user has roles that are assigned to them. Each role seperately has authorizations/permissions assigned to them. So when a user or users are given a role, they get all of the granular authorizations that are assigned to them. That means, if a group of users with "Role A" need a new authorization, it can be assigned to "Role A" and everyone with that role will get it immediately. There is no need to assign that authorization to every individual in that role.

The need at hand is to integrate Casbin into the project to facilitate that functionality. The endpoints have to generally work the same way; the project still needs to support an RBAC auth system.
