# Auth Service

This service handles all authentication and authorization needs for applications using JSON Web Tokens.

## Quick Start

Make sure your environment variables are set in a `.envrc` file (see the required variables below). There's a `sample_envrc` file provided for your convenience. For the quick start, the `MONGODB_URL` variable will be configured automatically.

Run the make command to spin up the whole stack.

```
make up
```

Check out the running auth service in the Demo Bench. Run the command and then go to `localhost:3000` in your browser.

```
make demo
```

Shut it all down with the down command.

```
make down
```

## Environment Variables

| Name (Required \*) | Description                                                                                                                                                                                                                                                                                               | Example                                           |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| GOOGLE_CLIENT_ID\* | This ID is required to decode Google Auth tokens, and it can be found in the Google Cloud Console.                                                                                                                                                                                                        | token.apps.googleusercontent.com                  |
| JWT_SECRET\*       | This key is used to encode and decode JWT's sent to clients. It should be a cryptic string that is shared across services that need to decode the JWT.                                                                                                                                                    | khMSpZkNsjwr                                      |
| MONGODB_URL\*      | The connection string to the MongoDB instance.                                                                                                                                                                                                                                                            | mongodb://username:mypassword@ehps.university.edu |
| ROOT_ADMIN_EMAIL   | The email address of a standing "break glass" identity that bypasses all authorization checks. Used to bootstrap the first role/permissions on a fresh system, and as a permanent recovery path if admin roles ever get misconfigured. Treat it like a secret; leave it unset once it's no longer needed. | you@university.edu                                |

## Minimum Database Requirements

A MongoDB database is required for this service to work. One database should exist called `auth_service`. For development purposes, a MongoDB instance can be spun up easily with docker:

```
docker run -p 27017:27017 --name auth-db -d mongo
```

**Note:** The casbin library will set up and manage a `casbin_rule` collection. Don't edit that data manually — only casbin should manage the data in that collection.

## Bootstrapping the First Admin

Roles and permissions are managed with [casbin](https://casbin.org/), and every role-management endpoint requires the requester to already have a permission granted through casbin. On a fresh system nobody has one, so `ROOT_ADMIN_EMAIL` provides a way in:

1. Set `ROOT_ADMIN_EMAIL` to your own email address in the environment.
2. Sign in as that email through the normal authentication flow (`/google-sign-in`).
3. Using the auth token (from step 2 in the demo website), call `PUT /update-role-permissions` to define an initial role, e.g. grant an `admin` role `roleupdate` and `assign` access to itself and to any other roles it should manage. `roleupdate` covers a role's permissions and inheritance; `assign` covers granting or revoking the role on accounts.
4. Call `PUT /update-account-roles` to grant yourself (or other accounts) that role.
5. From here on, accounts with that role can manage roles/permissions on their own — `ROOT_ADMIN_EMAIL` can be left set as a permanent recovery path or unset once you're confident real admin accounts are in place. While it's set, it's a standing bypass of all authorization checks, so treat it like a secret.

## Service Accounts

Backend services authenticate as **Google Cloud service accounts**, the same way browser apps authenticate people: the service gets a Google-signed ID token on its own, then exchanges it for this service's auth token.

```python
import requests
import google.auth.transport.requests
from google.oauth2 import id_token

# On Google Cloud this uses the metadata server; elsewhere, GOOGLE_APPLICATION_CREDENTIALS.
google_token = id_token.fetch_id_token(google.auth.transport.requests.Request(), GOOGLE_CLIENT_ID)
response = requests.post(f'{AUTH_SERVICE}/service-account/google-sign-in', json={'token': google_token})
auth_token = response.json()['token']
```

For local testing (and the demo website), mint the same kind of token from a service account's JSON key file:

```
python -m util.service_account_credential path/to/key.json
```

It reads `GOOGLE_CLIENT_ID` from the environment and uses it as the token's audience. Pass `-` instead of a path to read the key from stdin. From Python, `util.service_account_credential.mint_credential(key)` does the same thing. Key files are long-lived secrets: keep them out of the repo, and prefer attaching the service account to the workload on Google Cloud, where no key is needed.

Service accounts work like people: any service account can sign in, and what it can do comes from the roles granted to its email through `PUT /update-account-roles`. A service account with no roles gets a token with no permissions, just like an unknown user. The differences:

- **Separate endpoints.** `/google-sign-in` rejects service accounts, and `/service-account/google-sign-in` only accepts them.
- **The audience is `GOOGLE_CLIENT_ID`.** A service account picks the audience when it mints an ID token, and it must use this service's `GOOGLE_CLIENT_ID`, the same audience user tokens have.
- **No refresh tokens.** The auth token still expires after 15 minutes; the service mints a new ID token and signs in again. `/refresh-token` rejects service accounts.
- **Tokens say who's calling.** Every token payload has an `account_type` of `user` or `service`.

To cut off a service account, remove its roles. Auth tokens it already holds keep their old roles until they expire, within 15 minutes.

## Role Metadata

A role can optionally carry display metadata: an `alias` (for example, `security-liaison` → `Security Liaison`), `tags`, and a `description`. Metadata lives in its own `role_metadata` collection, separate from casbin, so it never affects permissions, inheritance, or tokens. A role doesn't need metadata, and metadata doesn't need the role to exist in casbin yet. Aliases are unique across roles, ignoring case.

This service doesn't decide what kinds of roles exist. Instead, you register whichever tags make sense for your system in the `role_tags` collection, then assign any of them to a role. For example, to classify each role as either a user role or a feature flag, register `User` and `Feature` once and give each role one of them. The service only checks that assigned tags are registered; conventions like "exactly one of `User` or `Feature`" are up to you. Tags can have a `description` too.


## Impersonation

`POST /impersonate` with `{"email": "<user email>"}` returns an auth token for that user, so support staff can see exactly what they see in other services.

- **Permission.** The requester needs `auth:impersonate`. `auth` is a resource reserved by this service: it can't be used as a role name. Anyone with `roleupdate` on a role can grant it `auth:*` permissions (e.g. `PUT /update-role-permissions` adding `{"obj": "auth", "act": "impersonate"}` to a `support` role).
- **Access token only.** The response is `{"token": "...", "payload": {...}}`, like the sign-in endpoints. No refresh token is issued, so the session ends when the token expires after 15 minutes.
- **Marked tokens.** The payload is the target user's, plus `impersonated_by` with the impersonator's email. Downstream services can use it to show a banner or audit actions.
- **Not usable here.** This service rejects impersonation tokens on every endpoint except `/login`, including `/impersonate` and `/refresh-token`.
- **Protected targets.** Service accounts and `ROOT_ADMIN_EMAIL` can't be impersonated.
- **Logged.** Each use is logged at INFO (`<impersonator> impersonated <user>`), and each denied attempt at WARNING.

Every token carries a `token_type`: `access` for auth tokens (including impersonation tokens) and `refresh` for refresh tokens. `/refresh-token` accepts only refresh tokens, and this service accepts only access tokens in the `Authorization` header. Other services should also check for `token_type: access`. Tokens issued before this change don't have the claim, so those users sign in again once.

## Running on your Local Machine

Install dependencies.

```
make setup
```

Make sure the required environment variables are set, then run the project.

```
make run-dev
```

## Running the Tests

The tests need a MongoDB instance to run against. The easiest way to run them is:

```
make test
```

This spins up a temporary Mongo container, runs `pytest` against it, then shuts the container down and removes it (along with its volume) when the tests finish.

If you already have the full stack running (`make up`), you can instead run tests inside the app container:

```
docker exec -it auth-service sh
```

Then run `pytest`.

## Updating Requirements

Whenever you need to install a new package, add it to the `pyproject.toml` file in the dependencies array. Then, run the `update-requirements` command.

```
make update-requirements
```

This will generate a new set of base and dev requirements that are installed when the project is set up.

## Demo

You can see a demo of this service and how it works by trying it out in the demo bench. The site is provided in the `demo-website` folder and must be served over port 3000 (or whichever port it configured in Google Cloud Platform) to work properly with Google Identity Services.

**Before running the website, set the Client ID on line 6 in `./demo-website/main.js`. It's the same as the `GOOGLE_CLIENT_ID` environment variable in this document.**

Then you can run the demo command to serve the page.

```
make demo
```

## Endpoints

To view the REST endpoints for this API, run the app, then go to `/docs` in the browser.
