import os
from dotenv import load_dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from services.tfidf_service import TFIDFProductService
from routes import tfidf_products_routes as tfidf_products
from utils.redis_utils import cache_data

load_dotenv()
product_service = TFIDFProductService()

# Hàm tính toán và cache dữ liệu
async def precompute_and_cache_data():
    products_df = product_service.get_products_from_db()
    tfidf_matrix = product_service.compute_tfidf_matrix(products_df)
    cache_data('products', products_df)
    cache_data('tfidf_matrix', tfidf_matrix)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await precompute_and_cache_data()
    yield

app = FastAPI(lifespan=lifespan)

SERVER = os.getenv('SERVER')
origins = [
    SERVER
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include your routers
app.include_router(tfidf_products.router)
