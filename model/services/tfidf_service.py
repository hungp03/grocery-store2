import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from entities.base import Product, Category
from utils.redis_utils import get_cached_data, cache_data
from fastapi import HTTPException

load_dotenv()

DATABASE_URL = os.getenv("DB_URL")

class TFIDFProductService:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        self.vectorizer = TfidfVectorizer()

    def get_products_from_db(self):
        session = self.Session()
        try:
            results = (
                session.query(Product, Category)
                .join(Category, Product.category_id == Category.id)
                .all()
            )
            products_data = [{
                'id': product.id,
                'product_name': product.product_name,
                'price': product.price,
                'rating': product.rating,
                'category': category.name,
                'description': product.description
            } for product, category in results]
        finally:
            session.close()
        
        return pd.DataFrame(products_data)

    def compute_tfidf_matrix(self, products_df):
        products_df['combined_features'] = products_df['product_name'] +" " + products_df['category'] + " " + products_df['description'].fillna('')
        tfidf_matrix = self.vectorizer.fit_transform(products_df['combined_features'])
        return tfidf_matrix

    def find_similar(self, input_text, products_df, tfidf_matrix, n=10):
        # Ensure vectorizer is fitted before transforming
        if not hasattr(self.vectorizer, 'vocabulary_'):
            # Fit the vectorizer if not fitted
            self.compute_tfidf_matrix(products_df) 

        input_vector = self.vectorizer.transform([input_text])
        similarities = cosine_similarity(input_vector, tfidf_matrix)[0]
        top_n_indices = np.argsort(similarities)[::-1][:n]
        similar_product_ids = products_df.iloc[top_n_indices]['id'].tolist()
        return similar_product_ids
    
    def search_similar_products(self, product_name: str, page: int = 1, pagesize: int = 10, n: int = 20):
        products_df = get_cached_data('products')
        tfidf_matrix = get_cached_data('tfidf_matrix')

        if products_df is None or tfidf_matrix is None:
            products_df = self.get_products_from_db()
            tfidf_matrix = self.compute_tfidf_matrix(products_df)
            cache_data('products', products_df)
            cache_data('tfidf_matrix', tfidf_matrix)

        similar_product_ids = self.find_similar(product_name, products_df, tfidf_matrix, n)

        if not similar_product_ids:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm tương tự")

        # Tính toán chỉ số bắt đầu và kết thúc cho phân trang
        start_index = (page - 1) * pagesize
        end_index = start_index + pagesize

        # Lấy phần tử con (slice) của danh sách sản phẩm tương tự dựa trên page và pagesize
        paged_similar_product_ids = similar_product_ids[start_index:end_index]

        return paged_similar_product_ids

    def get_similar_products_by_id(self, product_id: int, n=12):
        products_df = get_cached_data('products')
        tfidf_matrix = get_cached_data('tfidf_matrix')

        if products_df is None or tfidf_matrix is None:
            products_df = self.get_products_from_db()
            tfidf_matrix = self.compute_tfidf_matrix(products_df)
            cache_data('products', products_df)
            cache_data('tfidf_matrix', tfidf_matrix)

        product_row = products_df[products_df['id'] == product_id]

        if product_row.empty:
            raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")

        input_text = product_row.iloc[0]['product_name'] + " " + product_row.iloc[0]['category'] + " " + (product_row.iloc[0]['description'] or '')
        similar_product_ids = self.find_similar(input_text, products_df, tfidf_matrix, n + 1)

        # Exclude the product itself from the similar products list
        similar_product_ids = [id_ for id_ in similar_product_ids if id_ != product_id]

        if not similar_product_ids:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm tương tự")

        return similar_product_ids
