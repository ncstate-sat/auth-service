from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from controllers.authentication import router as authentication_router
load_dotenv()


origins = ['http://localhost', 'http://localhost:3000']

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/')
def read_root():
    return {'message': 'Go to \'/docs\' to view the endpoints and their functions.'}


app.include_router(authentication_router)
