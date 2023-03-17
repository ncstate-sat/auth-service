# Auth Service

This service handles all authentication and authorization needs for applications using JSON Web Tokens.

## Environment Variables

| Name (Required \*)      | Description                                                                                                                                                                                               | Example                                   |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| GOOGLE_CLIENT_ID\*      | This ID is required to decode Google Auth tokens, and it can be found in the Google Cloud Console.                                                                                                        | token.apps.googleusercontent.com          |
| JWT_SECRET\*            | This key is used to encode and decode JWT's sent to clients. It should be a cryptic string that is shared across services that need to decode the JWT.                                                    | khMSpZkNsjwr                              |
| MONGODB_URL\*           | The connection string to the MongoDB instance.  | mongodb://username:mypassword@ehps.university.edu |

## Minimum Database Requirements

<details>
<summary>Required: Database + Collection</summary>
A MongoDB database is required for this service to work. One database should exist called `Accounts`, and it should contain two collections called `accounts` and `roles`.
</details>
<details>
<summary>Database Setup</summary>
Set up at least one account and one role according to the database schema in the section below.
</details>
<br>
For development purposes, a MongoDB instance can be spun up easily with docker:

```
docker run -p 27017:27017 --name auth-db -d mongo
```

## Database Schema

### Collection: `accounts`

Documents in the `accounts` collection have three attributes (not including `_id`).
| Name | Value | Type | Example |
| --- | --- | --- | --- |
| email | The full email address of the user. | String | user@university.edu |
| campus_id | The campus_id of the account. | String | 000101234 |
| roles | An array of roles assigned to the individual of the account. | Array[String] | [admin] |

### Collection: `roles`

Documents in the `roles` collection have two attributes (not including `_id`).
| Name | Value | Type | Example |
| --- | --- | --- | --- |
| name | The name of the role. This will appear in the `roles` attribute in account documents for anyone who has the role. | String | admin |
| authorizations | A dictionary of values defining the authorizations for the role | Dict[String] | { '\_read': [], '\_write': [], 'root': true } |

The authorizations dictionary can have any values; they'll appear in the token payload. There are three protected values for this dictionary, however.

- `root`: This authorization means the account can read and write to anything without restrictions.
- `_read`: This is an array of roles. Users can query this service for other accounts by role, and this defines which accounts are allowed to be queried. For example, a user with a `_read` value of `["liaison"]` will only be able to query liaison users.
- `_write`: This is an array of roles. Users can assign roles if this is in their `_write` array. For example, a user with a `_write` value of `["liaison"]` will only be able to assign the `liaison` role to other users.

### Example

```json
"roles": [
    {
        "_id": ObjectId('asdf'),
        "name": "admin",
        "authorizations": {
            "root": true,
            "_read": ["admin"],
            "_write": ["admin"]
        }
    }
]

"accounts": [
    {
        "_id": ObjectId('asdf'),
        "email": "user@university.edu",
        "campus_id": "200103374",
        "roles": ["admin"]
    }
]
```

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

To run tests within a docker container, docker exec into the container.

```
docker exec -it auth-service sh
```

Then run `pytest`.

## Demo

You can see a demonstration of this service by trying it out in a webpage. A demo website is provided in the `demo-website` folder. The contents of the folder must be served over port 3000 (or whichever port it configured in Google Cloud Platform) to work properly with Google Identity Services.

**Before running the website, set the Client ID on line 123 in `index.html`. It's the same as the `GOOGLE_CLIENT_ID` environment variable in this document.**

You can serve the folder easily with the `http-server` package.

```
npm install -g http-server
http-server -p 3000 ./demo-website
```

## Endpoints

To view the REST endpoints for this API, run the app, then go to `/docs` in the browser.
