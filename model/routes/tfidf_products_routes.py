from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from services.tfidf_service import TFIDFProductService
from typing import Optional
router = APIRouter()
product_service = TFIDFProductService()

@router.get('/search/{word}')
def search(word: str, page: Optional[int] = 1, pagesize: Optional[int] = 10):
    try:
        similar_product_ids = product_service.search_similar_products(word, page, pagesize)
        response_data = {"status_code": 200, "data": similar_product_ids}
        return JSONResponse(content=response_data)
    except HTTPException as e:
        raise e

@router.get('/similar/{product_id}')
def get_similar_products(product_id: int):
    try:
        similar_product_ids = product_service.get_similar_products_by_id(product_id)
        response_data = {"status_code": 200, "data": similar_product_ids}
        return JSONResponse(content=response_data)
    except HTTPException as e:
        raise e
