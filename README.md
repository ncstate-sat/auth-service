# Auth Microservice
This microservice handles all authentication and authorization needs for SAT applications using JSON Web Tokens.

## Required Environment Variables
- `GOOGLE_CLIENT_ID`: This ID is required to decode Google Auth tokens.
- `JWT_SECRET`: This key is used to encode and decode JWT's sent to clients.

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

## Endpoints
To view the REST endpoints for this API, run the app, then go to `/docs` in the browser.