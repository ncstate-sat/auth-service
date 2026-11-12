"""
The starting point for the auth service.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from controllers.authentication import router as authentication_router
from controllers.authorization import router as authorization_router
from controllers.role_metadata import router as role_metadata_router
from controllers.role_tags import router as role_tags_router
from models.RoleMetadata import RoleMetadata
from models.RoleTag import RoleTag


DESCRIPTION = """
Handle authentication and authorization in your app. Sign in with Google and get back a token that will authenticate the user across multiple services and keep track of all authorizations across all of those services.

## Authentication Methods
Right now, only Google Sign In is supported. More ways to sign in can be added in the future. When a token from Google is passed into the appropriate endpoint, a new token is generated with the user's data. That new token is sent back to the client, and it is that token which is used between the services. The Google token is only used once to initially authenticate.

## Authorization
The payload of the token contains the user's email address, their roles, and a flattened list of permissions derived from those roles. Here's what a payload could look like:
```
{
    "email": "user@university.edu",
    "roles": ["admin"],
    "permissions": ["member:read", "member:write"]
}
```
Every payload also carries an `account_type` of either `user` or `service`, so a service receiving the token can tell whether a person or another service is calling it.

Roles and permissions are managed with [casbin](https://casbin.org/). Each permission is a `resource:action` pair granted to a role (for example, `member:write` lets a role grant or revoke the `member` role on other accounts), and can be changed at any time. Users can be assigned any number of roles, and they inherit every permission granted to each of those roles.

## Token Expiration & Refresh
Each auth JWT expires 15 minutes after it's generated. After expiring, the token is useless. To keep using the apps and services, a new token will have to be generated. So the user doesn't have to sign in every 15 minutes, a refresh token is used. Upon signing in, an auth token and refresh token is sent to the client. After the auth token expires, the refresh token can be used to generate another auth token. That refresh token expires 2 days after being generated, and it's replaced every time the auth token is replaced.

## Service Accounts
Backend services authenticate as Google Cloud service accounts. A service mints a Google-signed ID token for its own service account (for example, with `google.oauth2.id_token.fetch_id_token`) and exchanges it at `/service-account/google-sign-in` for an auth token, the same way a browser app exchanges a user's credential at `/google-sign-in`.

Service accounts get roles through `/update-account-roles` like any other account. Service accounts don't receive refresh tokens; when the auth token expires, they mint a new ID token and sign in again.

## Role Metadata
A role can optionally carry an `alias` (a display name, unique across roles regardless of case) and `tags`. Which tags exist is up to you: register them at `/role-tags` (for example, `User` and `Feature`), then assign any of them to a role. This metadata is stored separately from casbin and never changes a role's permissions, inheritance, or accounts. `POST /role-metadata` creates a role's metadata or updates it if it already exists, and `GET /role-metadata?tag=...` lists the roles with a given tag. A tag can't be deleted while any role still has it. These endpoints are not auth-protected yet.
"""


@asynccontextmanager
async def lifespan(_app):
    RoleMetadata.ensure_indexes()
    RoleTag.ensure_indexes()
    yield

app = FastAPI(
    title='Auth Service',
    description=DESCRIPTION,
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/', tags=['Default'])
def welcome():
    """Simple GET request that returns a helpful message."""
    return {'message': 'Go to \'/docs\' to view the endpoints and their functions.'}


app.include_router(authentication_router)
app.include_router(authorization_router)
app.include_router(role_metadata_router)
app.include_router(role_tags_router)
