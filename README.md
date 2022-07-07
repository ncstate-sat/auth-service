# Auth Service
This service handles all authentication and authorization needs for SAT applications using JSON Web Tokens.

## Required Environment Variables
- `GOOGLE_CLIENT_ID`: This ID is required to decode Google Auth tokens.
- `JWT_SECRET`: This key is used to encode and decode JWT's sent to clients.
- `MONGODB_URL`: The connection string to the MongoDB instance.

## Other Requirements
A MongoDB database is required for this service to work. The database name should be `Accounts`, and it should contain one collection called `accounts`. A MongoDB instance can be spun up easily with docker:
```
docker run -p 27017:27017 --name auth-db -d mongo
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