"""
The starting point for the auth service.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from controllers.authentication import router as authentication_router
from controllers.authorization import router as authorization_router
load_dotenv()


DESCRIPTION = """
Handle authentication and authorization in your app. Sign in with Google and get back a token that will authenticate the user across multiple services and keep track of all authorizations across all of those services.

## Authentication Methods
Right now, only Google Sign In is supported. More ways to sign in can be added in the future. When a token from Google is passed into the appropriate endpoint, a new token is generated with the user's data. That new token is sent back to the client, and it is that token which is used between the services. The Google token is only used once to initially authenticate.

## Authorization
The payload of the token contains the user's email address, their roles, and their authorizations. Here's what a payload could look like:
```
{
    "email": "user@university.edu",
    "roles": ["admin"],
    "authorizations: {
        root: true
    }
}
```
Each role has a number of authorizations tied to it. These authorizations are set up in the `roles` collection and can be changed at any time. Users can be assigned any number or roles, and they will inherit every authorization granted in each role. The authorizations set up in each role are arbitrary and can be set up as needed for each service.

## Token Expiration & Refresh
Each auth JWT expires 15 minutes after it's generated. After expiring, the token is useless. To keep using the apps and services, a new token will have to be generated. So the user doesn't have to sign in every 15 minutes, a refresh token is used. Upon signing in, an auth token and refresh token is sent to the client. After the auth token expires, the refresh token can be used to generate another auth token. That refresh token expires 2 days after being generated, and it's replaced every time the auth token is replaced.
"""

app = FastAPI(
    title='Auth Service',
    description=DESCRIPTION,
    version="1.0.1"
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
