# Standard library imports
import os
import datetime

# Third-party imports
import joblib
import numpy as np
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from dotenv import load_dotenv
from fastapi import HTTPException
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sentence_transformers import SentenceTransformer
from annoy import AnnoyIndex
import mysql.connector
# Local imports
from entities.base import Product
from utils.redis_utils import get_cached_data, cache_data, delete_key


load_dotenv()

DATABASE_URL = os.getenv("DB_URL")
DB_host=os.getenv("DB_host")
DB_user=os.getenv("DB_user")
DB_password=os.getenv("DB_password")
DB_database=os.getenv("DB_database")

SENTENCE_TRANSFORMER_MODEL_FILE = 'sentence_transformer_model.pkl'

class RecommendationService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RecommendationService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)

        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self._schedule_data_refresh()
        self._model = None
        self._annoy_index = None
        self._initialized = True

    
    def _initialize_cache(self):
        """Tạo và lưu cache nếu chưa tồn tại."""
        # Kiểm tra cache cho product_embeddings
        if not get_cached_data('product_embeddings'):
            print("Cache for product_embeddings not found. Generating...")
            product_embeddings = self._load_products_embeddings()
            cache_data('product_embeddings', product_embeddings)
            print("Cache for product_embeddings has been initialized.")

        # Kiểm tra cache cho user_data
        if not get_cached_data('user_data'):
            print("Cache for user_data not found. Generating...")
            user_data = self._load_user_data()
            cache_data('user_data', user_data)
            print("Cache for user_data has been initialized.")

        # Kiểm tra cache cho user_vectors và behavior_matrix
        if not get_cached_data('user_vectors') or not get_cached_data('behavior_matrix'):
            print("Cache for user_vectors or behavior_matrix not found. Generating...")
            user_vectors, behavior_matrix = self._compute_user_vectors()
            cache_data('user_vectors', user_vectors)
            cache_data('behavior_matrix', behavior_matrix)
            print("Cache for user_vectors and behavior_matrix has been initialized.")

    def _schedule_data_refresh(self):
        self.scheduler.add_job(self.refresh_product_embeddings, 'interval', hours=12, id='refresh_product_embeddings')
        self.scheduler.add_job(self.refresh_user_behavior, 'interval', hours=3, id='refresh_user_behavior')
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    def _job_listener(self, event):
        if event.exception:
            print(f"Công việch {event.job_id} bị lỗi")
        else:
            print(f"Công việc {event.job_id} hoàn thành thành công")

    @property
    def model(self):
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def _load_model(self):
        if os.path.exists(SENTENCE_TRANSFORMER_MODEL_FILE):
            return joblib.load(SENTENCE_TRANSFORMER_MODEL_FILE)
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        joblib.dump(model, SENTENCE_TRANSFORMER_MODEL_FILE)
        return model
    
    @property
    def annoy_index(self):
        if self._annoy_index is None:
            self._annoy_index = self._build_annoy_index()
        return self._annoy_index
    
    def _build_annoy_index(self):
        """Xây dựng cây Annoy cho vector người dùng"""
        user_vectors, _ = self.get_user_vectors()
        vector_dim = user_vectors.shape[1]
        index = AnnoyIndex(vector_dim, 'angular')
        for i, vec in enumerate(user_vectors):
            index.add_item(i, vec)
        index.build(10)
        return index

    def refresh_product_embeddings(self):
        delete_key("product_embeddings")
        print(f"Làm mới embedding sản phẩm vào lúc {datetime.datetime.now()}")
        product_embeddings = self._load_products_embeddings()
        cache_data('product_embeddings', product_embeddings)

    def refresh_user_behavior(self):
        delete_key("user_data")
        print(f"Làm mới ma trận hành vi người dùng vào lúc {datetime.datetime.now()}")
        user_data = self._load_user_data()
        cache_data('user_data', user_data)

        delete_key("user_vectors")
        delete_key("behavior_matrix")
        user_vectors, behavior_matrix = self._compute_user_vectors()
        cache_data("user_vectors", user_vectors)
        cache_data("behavior_matrix", behavior_matrix)

    def _load_products_embeddings(self):
        session = self.Session()
        try:
            results = session.query(Product.id, Product.embedding).all()
            product_embeddings = {
                product_id: np.frombuffer(embedding, dtype=np.float32)
                for product_id, embedding in results if embedding
            }
            return product_embeddings
        finally:
            session.close()

    def _load_user_data(self):
        user_data = get_cached_data('user_data')
        if user_data is not None:
            return user_data
        
        user_data = self._get_user_behavior_from_db()
        cache_data('user_data', user_data)
        return user_data

    def _get_user_behavior_from_db(self):
        try:
            connection = mysql.connector.connect(
                host=DB_host,
                user=DB_user,
                password=DB_password,
                database=DB_database
            )
            
            cursor = connection.cursor(dictionary=True)
            
            cursor.callproc('GetUserBehavior')
            results = []
            for result in cursor.stored_results():
                results.append(result.fetchall())
            
            df = pd.DataFrame(results[0]) if results else pd.DataFrame()
            
            # Đóng cursor và connection
            cursor.close()
            connection.close()
            
            return df
        except mysql.connector.Error as e:
            print(f"Lỗi khi gọi Stored Procedure: {e}")
            raise



    def _compute_user_vectors(self):
        user_data = self._load_user_data()
        feedback_vectors = user_data['feedback_description'].apply(
            lambda x: self.model.encode(x) if x and x.strip() else None
        ).dropna()
        
        default_vector = np.mean(np.stack(feedback_vectors), axis=0) if len(feedback_vectors) > 0 else np.zeros(self.model.get_sentence_embedding_dimension())
        user_data['feedback_vector'] = user_data['feedback_description'].apply(
            lambda x: self.model.encode(x) if x and x.strip() else default_vector
        )
        
        grouped_vectors = user_data.groupby('user_id')['feedback_vector'].apply(lambda x: np.mean(np.stack(x), axis=0))
        behavior_matrix = user_data.pivot_table(index='user_id', columns='product_id', values=['purchase', 'rating_star', 'in_wishlist'], fill_value=0)
        user_vectors = np.hstack((StandardScaler().fit_transform(behavior_matrix), np.stack(grouped_vectors)))
        cache_data("user_vectors", user_vectors)
        cache_data("behavior_matrix", behavior_matrix)
        return user_vectors, behavior_matrix

    def get_user_vectors(self):
        user_vectors = get_cached_data("user_vectors")
        behavior_matrix = get_cached_data("behavior_matrix")
        if user_vectors is None or behavior_matrix is None:
            user_vectors, behavior_matrix = self._compute_user_vectors()
        return user_vectors, behavior_matrix

    def recommend_products_for_user(self, user_id, top_n=18, similar_users_count=10):
        user_vectors, behavior_matrix = self.get_user_vectors()
        if user_id not in behavior_matrix.index:
            return None
        user_idx = behavior_matrix.index.get_loc(user_id)
        similar_user_indices = self.annoy_index.get_nns_by_item(user_idx, similar_users_count + 1)[1:]
        similar_user_ids = behavior_matrix.index[similar_user_indices]
        user_vector = user_vectors[user_idx].reshape(1, -1)
        similarities = cosine_similarity(user_vector, user_vectors[similar_user_indices])

        sorted_indices = np.argsort(similarities[0])[::-1]
        top_similar_user_ids = similar_user_ids[sorted_indices]
        us_data = self._load_user_data()

        user_purchases = set(us_data.loc[
            (us_data['user_id'] == user_id) & (us_data['purchase'] == 1),
            'product_id'
        ])

        similar_user_products = set(us_data.loc[
            (us_data['user_id'].isin(top_similar_user_ids)) & 
            ((us_data['purchase'] == 1) | (us_data['in_wishlist'] == 1)),
            'product_id'
        ])
        
   
        recommended_products = similar_user_products - user_purchases

        if len(recommended_products) < top_n:
            session = self.Session()
            try:
                excluded_products = recommended_products | user_purchases
                additional_products = session.query(Product.id)\
                    .filter(~Product.id.in_(excluded_products))\
                    .order_by(Product.rating.desc(), Product.sold.desc())\
                    .limit(top_n - len(recommended_products))\
                    .all()
                
                recommended_products.update([product[0] for product in additional_products])
            finally:
                session.close()

        return list(recommended_products)[:top_n]
    
    def find_similar_products(self, input_data, n=10, input_type="text"):
        if input_type == "text":
            input_embedding = self.model.encode(input_data, convert_to_tensor=False)
        elif input_type == "embedding":
            if not isinstance(input_data, np.ndarray):
                raise ValueError("require np.ndarray for embedding data")
            input_embedding = input_data
        else:
            raise ValueError("input_type must be 'text' or 'embedding'.")

        # Truy xuất product_embeddings từ Redis
        product_embeddings = get_cached_data('product_embeddings')
        if not product_embeddings:
            product_embeddings = self._load_products_embeddings()
            cache_data('product_embeddings', product_embeddings)

        embeddings_list = list(product_embeddings.values())
        product_ids = list(product_embeddings.keys())

        # Tính toán tương đồng cosine
        similarities = cosine_similarity([input_embedding], embeddings_list)[0]
        top_n_indices = np.argsort(-similarities)[:n]
        similar_product_ids = [product_ids[idx] for idx in top_n_indices]
        
        return similar_product_ids

    def search_similar_products_by_keyword(self, keyword, page=1, pagesize=10, n=20):
        similar_product_ids = self.find_similar_products(keyword, n, input_type="text")

        if not similar_product_ids:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm tương tự")

        start_index = (page - 1) * pagesize
        end_index = start_index + pagesize

        return similar_product_ids[start_index:end_index]
    
    def _get_product_embedding_by_id(self, product_id):
        embeddings = get_cached_data('product_embeddings')
        if embeddings is not None:
            if product_id in embeddings:
                return embeddings[product_id]

        # truy vấn từ db nếu không có cache
        session = self.Session()
        try:
            result = session.query(Product).filter(Product.id == product_id).first()
            if result and result.embedding:
                embedding = np.frombuffer(result.embedding, dtype=np.float32)
                return embedding
        finally:
            session.close()

        return None


    def get_similar_products_by_id(self, product_id: int, n=12):
        product_embedding = self._get_product_embedding_by_id(product_id)
        if product_embedding is None:
            raise HTTPException(status_code=404, detail="Embedding cho sản phẩm không tồn tại")

        similar_product_ids = self.find_similar_products(product_embedding, n + 1, input_type="embedding")
        similar_product_ids = [id_ for id_ in similar_product_ids if id_ != product_id]

        if not similar_product_ids:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm tương tự")

        return similar_product_ids[:n]
    
    def update_product_embedding(self, product_id):
        session = self.Session()
        try:
            product = (
                session.query(Product)
                .filter(Product.id == product_id)
                .first()
            )

            if not product:
                raise ValueError(f"Sản phẩm với ID {product_id} không tồn tại.")

            product_text = f"{product.product_name} {product.category.name} {product.description or ''}"
            new_embedding = self.model.encode(product_text, convert_to_tensor=False)

            product.embedding = np.asarray(new_embedding, dtype=np.float32).tobytes()
            session.commit()
            
            # Xóa cache embedding để refresh
            delete_key('product_embeddings')
            print(f"Đã cập nhật embedding cho sản phẩm ID {product_id}.")
        except Exception as e:
            session.rollback()
            print(f"Lỗi khi cập nhật embedding cho sản phẩm ID {product_id}: {e}")
            raise
        finally:
            session.close()