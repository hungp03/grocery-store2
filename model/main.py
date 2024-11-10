import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from services.recommendationService import RecommendationService
from routes import recommendation_routes as router

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    RecommendationService()
    yield

app = FastAPI(lifespan=lifespan)

SERVER = os.getenv('SERVER')
origins = [SERVER]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router.router)