from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from services.recommendationService import RecommendationService
from typing import Optional

router = APIRouter()
product_service = RecommendationService()

@router.get('/similar/{product_id}')
def get_similar_products(product_id: int):
    try:
        similar_product_ids = product_service.get_similar_products_by_id(product_id)
        response_data = {"status_code": 200, "data": similar_product_ids}
        return JSONResponse(content=response_data)
    except HTTPException as e:
        raise e

@router.get('/search/{word}')
def search(word: str, page: Optional[int] = 1, pagesize: Optional[int] = 10):

    try:
        product_ids = product_service.search_similar_products_by_keyword(word, page, pagesize)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    response_data = {
        "status_code": 200,
        "data": product_ids
    }

    return JSONResponse(content=response_data)

@router.get('/recommend/{userid}')
def recommend(userid: int):
    try:
        recommend_product_ids = product_service.recommend_products_for_user(userid)
        response_data = {"status_code": 200, "data": recommend_product_ids}
        return JSONResponse(content=response_data)
    except HTTPException as e:
        raise e