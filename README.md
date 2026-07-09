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
3. Using the auth token (from step 2 in the demo website), call `PUT /update-role-permissions` to define an initial role, e.g. grant an `admin` role `write` access to itself and to any other roles it should manage.
4. Call `PUT /update-account-roles` to grant yourself (or other accounts) that role.
5. From here on, accounts with that role can manage roles/permissions on their own — `ROOT_ADMIN_EMAIL` can be left set as a permanent recovery path or unset once you're confident real admin accounts are in place. While it's set, it's a standing bypass of all authorization checks, so treat it like a secret.

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

Run `pytest` in the terminal to run all tests.

To run tests within a docker container, docker exec into the container.

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
