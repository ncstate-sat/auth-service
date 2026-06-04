# Auth Service

This service handles all authentication and authorization needs for applications using JSON Web Tokens.

## How It Works

### Authentication

Clients authenticate by passing a Google Identity token to `POST /google-sign-in`. The service verifies it with Google, looks up (or auto-creates) the account in MongoDB, then issues two tokens:

- **Auth token** — a short-lived JWT (15 min) that contains the user's email, roles, and authorizations. Downstream services verify this token using the shared `JWT_SECRET` and read the payload to make access-control decisions without hitting this service.
- **Refresh token** — a longer-lived JWT (2 days) used to get a new auth token once the original expires, via `POST /refresh-token`.

### Authorization

Role-Based Access Control (RBAC) is managed by **[Casbin](https://casbin.org/)**, an access-control library. Casbin is the authoritative source for two things:

1. **Policies** — which roles are allowed to read or write which other roles. Stored in the `casbin_rules` MongoDB collection (managed automatically by the service).
2. **Role assignments** — which users belong to which roles. Also stored in `casbin_rules`.

MongoDB's `roles` collection stores the role definitions themselves: their names and any custom authorization flags (like `can_do_x: true`) that downstream services read from JWT payloads. The `accounts` collection stores account email addresses only.

On first boot, the service automatically migrates any existing `_read`/`_write` fields from the `roles` collection and any `roles` arrays from the `accounts` collection into Casbin. After that, `casbin_rules` is the single source of truth for all RBAC data.

## Environment Variables

| Name (Required \*)      | Description                                                                                                                                                                                               | Example                                   |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| GOOGLE_CLIENT_ID\*      | This ID is required to decode Google Auth tokens, and it can be found in the Google Cloud Console.                                                                                                        | token.apps.googleusercontent.com          |
| JWT_SECRET\*            | This key is used to encode and decode JWTs sent to clients. It should be a cryptic string that is shared across services that need to decode the JWT.                                                    | khMSpZkNsjwr                              |
| MONGODB_URL\*           | The connection string to the MongoDB instance.  | mongodb://username:mypassword@host |

## Minimum Database Requirements

<details>
<summary>Required: Database + Collections</summary>

A MongoDB database called `Accounts` is required with three collections:

- `accounts` — stores user email addresses.
- `roles` — stores role definitions and custom authorization flags.
- `casbin_rules` — created and managed automatically by the service. Do not modify this collection manually.

</details>
<details>
<summary>Database Setup</summary>

Set up at least one role document in the `roles` collection and one account document in the `accounts` collection. See the schema below. On first boot, the service migrates role permissions and account role assignments into Casbin automatically.

</details>
<br>

For development purposes, a MongoDB instance can be spun up easily with Docker:

```
docker run -p 27017:27017 --name auth-db -d mongo
```

## Database Schema

### Collection: `accounts`

Each document represents one user account.

| Name  | Value                              | Type   | Example             |
| ----- | ---------------------------------- | ------ | ------------------- |
| email | The full email address of the user | String | user@university.edu |

> **Note:** User-role assignments are stored in the `casbin_rules` collection by Casbin, not in account documents. Do not add a `roles` field here; it will be ignored.

### Collection: `roles`

Each document defines a role and its custom authorization flags.

| Name           | Value                                                              | Type        | Example                                  |
| -------------- | ------------------------------------------------------------------ | ----------- | ---------------------------------------- |
| name           | The name of the role                                               | String      | `admin`                                  |
| authorizations | A dictionary of custom flags that will be embedded in JWT payloads | Dict        | `{ "root": true, "can_do_x": true }`    |

Custom flags in `authorizations` can be anything — they are passed through to the JWT so downstream services can read them. There are two reserved keys:

- `root` — when `true`, this role bypasses all `_read`/`_write` restrictions and can read or write any role.
- `_read` / `_write` — **legacy fields.** These were used before Casbin was introduced and are only read during the one-time startup migration. After migration, role read/write permissions live in Casbin (`casbin_rules`) and these fields are no longer consulted.

### Collection: `casbin_rules` (managed automatically)

This collection is created and maintained by Casbin. Do not modify it manually unless you know what you are doing.

Each document is a Casbin rule of one of two types:

**Policy rule** (`ptype: "p"`) — grants a role permission to read or write another role:

| Field | Description        | Example values              |
| ----- | ------------------ | --------------------------- |
| ptype | Rule type          | `"p"`                       |
| v0    | Role being granted | `"admin"`                   |
| v1    | Target role (or `*` for all roles) | `"member"` / `"*"` |
| v2    | Action             | `"read"` or `"write"`       |

**Grouping rule** (`ptype: "g"`) — assigns a user to a role:

| Field | Description        | Example values              |
| ----- | ------------------ | --------------------------- |
| ptype | Rule type          | `"g"`                       |
| v0    | User email         | `"user@university.edu"`     |
| v1    | Role name          | `"admin"`                   |

### Example Documents

```json
// roles collection
[
    {
        "name": "admin",
        "authorizations": {
            "root": true
        }
    },
    {
        "name": "member",
        "authorizations": {
            "can_do_x": true,
            "can_do_y": true
        }
    }
]

// accounts collection
[
    { "email": "alice@university.edu" },
    { "email": "bob@university.edu" }
]

// casbin_rules collection (managed by the service)
[
    { "ptype": "p", "v0": "admin", "v1": "*", "v2": "read" },
    { "ptype": "p", "v0": "admin", "v1": "*", "v2": "write" },
    { "ptype": "g", "v0": "alice@university.edu", "v1": "admin" },
    { "ptype": "g", "v0": "bob@university.edu",   "v1": "member" }
]
```

## Configuring Roles and Permissions

### Adding a new role

1. Insert a document into the `roles` collection with a `name` and any custom `authorizations` flags.
2. Add the role's read/write policies to `casbin_rules`. For example, to let the new `liaison` role read other liaison accounts:
   ```json
   { "ptype": "p", "v0": "liaison", "v1": "liaison", "v2": "read" }
   ```
3. To also let admins manage liaisons, add write permission for the admin role:
   ```json
   { "ptype": "p", "v0": "admin", "v1": "liaison", "v2": "write" }
   ```

### Assigning roles to users

Use the `PUT /update-account-roles` endpoint (requires a token from an account with write permission over the target role):

```json
{
    "email": "user@university.edu",
    "add_roles": ["liaison"],
    "remove_roles": []
}
```

Alternatively, insert a grouping rule directly into `casbin_rules` and restart the service (the enforcer loads policies at startup):

```json
{ "ptype": "g", "v0": "user@university.edu", "v1": "liaison" }
```

### JWT payload structure

The auth token payload always includes:

```json
{
    "email": "user@university.edu",
    "roles": ["admin"],
    "authorizations": {
        "root": true,
        "_read": ["member"],
        "_write": ["member"]
    },
    "exp": 1234567890
}
```

- `roles` — the user's current roles, pulled from Casbin at token generation time.
- `authorizations._read` — roles this user can query via `GET /role-accounts`, derived from Casbin policies.
- `authorizations._write` — roles this user can assign/revoke via `PUT /update-account-roles`, derived from Casbin policies.
- Any other keys in `authorizations` (like `root`, `can_do_x`) come from the role's document in the `roles` collection.

## Running on your Local Machine

Install dependencies.

```
pip install -r requirements.txt
```

Make sure the required environment variables are set, then run the project.

```
uvicorn main:app --reload
```

## Running in a Docker Container

Build the image.

```
docker build -t auth-service .
```

Run the container, ensuring it's set up with the required environment variables.

```
docker run -p 8000:8000 --env-file .env auth-service
```

## Running the Tests

Run `pytest` in the terminal to run all tests.

To run tests within a Docker container, exec into the container:

```
docker exec -it auth-service sh
```

Then run `pytest`.

## Demo

You can see a demonstration of this service by trying it out in a webpage. A demo website is provided in the `demo-website` folder. The contents of the folder must be served over port 3000 (or whichever port is configured in Google Cloud Platform) to work properly with Google Identity Services.

**Before running the website, set the Client ID on line 123 in `index.html`. It's the same as the `GOOGLE_CLIENT_ID` environment variable in this document.**

You can serve the folder easily with the `http-server` package.

```
npm install -g http-server
http-server -p 3000 ./demo-website
```

## Endpoints

To view the REST endpoints for this API, run the app, then go to `/docs` in the browser.
