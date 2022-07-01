from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from controllers.authentication import router as authentication_router
from controllers.authorization import router as authorization_router
load_dotenv()


description = """
Handle authentication and authorization in your NCSU app. Sign in with Google and get back a token that will authenticate the user across multiple services and keep track of all authorizations across all of those services.

## Authentication Methods
Right now, only Google Sign In is supported. More ways to sign in can be added in the future. When a token from Google is passed into the appropriate endpoint, a new token is generated with the user's data. That new token is sent back to the client, and it is that token which is used between the services. The Google token is only used once to initially authenticate.

## Authorization
The payload of the token contains the user's email address, campus ID, and their authorizations. The authorization component is a dictionary where each key represents an application, and the value is whatever that app wants to store. Here's what a payload could look like:
```
{
    "email": "user@ncsu.edu",
    "campus_id: "200101234",
    "authorizations": {
        "some-app": {
            "read": True,
            "write": False
        }
    }
}
```
Each app can use the authorization endpoints to create and update whatever data they want for each user account. 
"""


origins = ['http://localhost', 'http://localhost:3000']

app = FastAPI(
    title='Auth Service',
    description=description,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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