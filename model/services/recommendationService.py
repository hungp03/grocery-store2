# Standard library imports
import os
import datetime
from functools import lru_cache

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

# Local imports
from entities.base import Product
from utils.redis_utils import get_cached_data, cache_data, delete_key

load_dotenv()

DATABASE_URL = os.getenv("DB_URL")
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
        
        # Khởi tạo scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        
        # Lên lịch các tác vụ làm mới dữ liệu
        self._schedule_data_refresh()
        
        # Lazy loading attributes
        self._model = None
        self._product_embeddings = None
        self._user_data = None
        self._user_vectors = None
        self._behavior_matrix = None
        self._annoy_index = None
        self._initialized = True

    @property
    def user_data(self):
        if self._user_data is None:
            self._user_data = self._load_user_data()
        return self._user_data
    
    def _schedule_data_refresh(self):
        # Lên lịch refresh embeddings sản phẩm mỗi 12 tiếng
        self.scheduler.add_job(self.refresh_product_embeddings, 'interval', hours=12, id='refresh_product_embeddings')
        # Lên lịch refresh hành vi người dùng mỗi 3 tiếng
        self.scheduler.add_job(self.refresh_user_behavior, 'interval', hours=3, id='refresh_user_behavior')
        # Lắng nghe sự kiện thực thi các tác vụ
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    def _job_listener(self, event):
        if event.exception:
            print(f"Công việch {event.job_id} bị lỗi")
        else:
            print(f"Công việc {event.job_id} hoàn thành thành công")

    def refresh_product_embeddings(self):
        """Làm mới embedding của sản phẩm"""
        print(f"Làm mới embedding sản phẩm vào lúc {datetime.datetime.now()}")
        delete_key("product_embeddings")
        
        # Nạp và cache lại embedding
        product_embeddings = self._load_products_embeddings()
        cache_data('product_embeddings', product_embeddings)

    def refresh_user_behavior(self):
        """Làm mới dữ liệu hành vi người dùng"""
        delete_key("user_data")
        print(f"Làm mới ma trận hành vi người dùng vào lúc {datetime.datetime.now()}")
        
        # Tải lại dữ liệu người dùng
        self._user_data = self._load_user_data()
        cache_data('user_data', self._user_data)

        # Reset vectors và matrix
        delete_key("user_vectors")
        delete_key("behavior_matrix")
        self._user_vectors, self._behavior_matrix = self._compute_user_vectors()
        
        # Tái cấu trúc cây annoy
        self._annoy_index = None
        self._annoy_index = self._build_annoy_index()
        print("Tái cấu trúc cây annoy")
        
        # Cache vectors và matrix
        cache_data("user_vectors", self._user_vectors)
        cache_data("behavior_matrix", self._behavior_matrix)

    @property
    def model(self):
        """Lazy load mô hình embedding"""
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def _load_model(self):
        """Tải hoặc tạo mô hình embedding"""
        if os.path.exists(SENTENCE_TRANSFORMER_MODEL_FILE):
            model = joblib.load(SENTENCE_TRANSFORMER_MODEL_FILE)
        else:
            model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            joblib.dump(model, SENTENCE_TRANSFORMER_MODEL_FILE)
        return model

    def _load_products_embeddings(self):
        """Tải embedding sản phẩm từ cơ sở dữ liệu"""
        session = self.Session()
        try:
            # Truy vấn chỉ ID và embedding
            results = session.query(Product.id, Product.embedding).all()
            
            product_embeddings = {}
            for product_id, embedding in results:
                if embedding:
                    product_embeddings[product_id] = np.frombuffer(embedding, dtype=np.float32)
            return product_embeddings
        finally:
            session.close()

    @property
    def product_embeddings(self):
        """Truy xuất embedding sản phẩm, ưu tiên cache"""
        if self._product_embeddings is None:
            cached_embeddings = get_cached_data('product_embeddings')
            if cached_embeddings:
                self._product_embeddings = cached_embeddings
            else:
                self._product_embeddings = self._load_products_embeddings()
                cache_data('product_embeddings', self._product_embeddings)
        return self._product_embeddings

    def _load_user_data(self):
        """Tải dữ liệu hành vi người dùng"""
        cached_user_data = get_cached_data('user_data')
        if cached_user_data is not None:
            return cached_user_data
        
        user_data = self._get_user_behavior_from_db()
        cache_data('user_data', user_data)
        return user_data

    @lru_cache(maxsize=1)
    def _get_user_behavior_from_db(self):
        """Truy vấn hành vi người dùng từ cơ sở dữ liệu"""
        query = "CALL GetUserBehavior();"
        
        with self.engine.connect() as conn:
            cursor = conn.connection.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            cursor.close()

        return pd.DataFrame(result, columns=columns)

    def update_product_embedding(self, product_id):
        """Cập nhật embedding cho một sản phẩm"""
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

    def get_user_vectors(self):
        """Lấy vector người dùng"""
        if self._user_vectors is None or self._behavior_matrix is None:
            cached_vectors = get_cached_data("user_vectors")
            cached_matrix = get_cached_data("behavior_matrix")
            
            if cached_vectors is not None and cached_matrix is not None:
                self._user_vectors = cached_vectors
                self._behavior_matrix = cached_matrix
            else:
                self._user_vectors, self._behavior_matrix = self._compute_user_vectors()
        
        return self._user_vectors, self._behavior_matrix

    def _compute_user_vectors(self):
        cached_vectors = get_cached_data("user_vectors")
        cached_matrix = get_cached_data("behavior_matrix")
        if cached_vectors is not None and cached_matrix is not None:
            return cached_vectors, cached_matrix

        user_data_df = self.user_data
        # Tính toán vector phản hồi hợp lệ
        valid_feedback_vectors = user_data_df['feedback_description'].apply(
            lambda x: self.model.encode(x) if x and x.strip() != '' else None
        ).dropna()  # Loại bỏ các giá trị None
        
        # Tính toán vector đặc trưng bằng cách tính trung bình của tất cả các vector hợp lệ
        feature_vector = np.mean(np.stack(valid_feedback_vectors), axis=0) if len(valid_feedback_vectors) > 0 else np.zeros(self.model.get_sentence_embedding_dimension())
        
        # Thay thế None bằng vector đặc trưng
        user_data_df['feedback_vector'] = user_data_df['feedback_description'].apply(
            lambda x: self.model.encode(x) if x and x.strip() != '' else feature_vector
        )

        feedback_vectors = (
            user_data_df.dropna(subset=['feedback_vector'])
            .groupby('user_id')['feedback_vector']
            .apply(lambda x: np.mean(np.stack(x), axis=0))
        )

        behavior_matrix = user_data_df.pivot_table(
            index='user_id', 
            columns='product_id', 
            values=['purchase', 'rating_star', 'in_wishlist'], 
            fill_value=0
        )
        behavior_vectors = StandardScaler().fit_transform(behavior_matrix)
        user_vectors = np.hstack((behavior_vectors, np.stack(feedback_vectors)))
        
        cache_data("user_vectors", user_vectors)
        cache_data("behavior_matrix", behavior_matrix)
        #print(user_vectors)
        return user_vectors, behavior_matrix

    @property
    def annoy_index(self):
        """Xây dựng và trả về Annoy Index"""
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

    def find_similar_products(self, input_data, n=10, input_type="text"):
        """Tìm sản phẩm tương tự"""
        if input_type == "text":
            input_embedding = self.model.encode(input_data, convert_to_tensor=False)
        elif input_type == "embedding":
            if not isinstance(input_data, np.ndarray):
                raise ValueError("require np.ndarray for embedding data")
            input_embedding = input_data
        else:
            raise ValueError("input_type must be 'text' or 'embedding'.")

        embeddings_list = list(self.product_embeddings.values())
        product_ids = list(self.product_embeddings.keys())

        similarities = cosine_similarity([input_embedding], embeddings_list)[0]
        top_n_indices = np.argsort(-similarities)[:n]
        similar_product_ids = [product_ids[idx] for idx in top_n_indices]
        
        return similar_product_ids

    def recommend_products_for_user(self, user_id, top_n=18, similar_users_count=10):
        """Đề xuất sản phẩm cho người dùng"""
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

        user_purchases = set(self.user_data.loc[
            (self.user_data['user_id'] == user_id) & (self.user_data['purchase'] == 1),
            'product_id'
        ])

        similar_user_products = set(self.user_data.loc[
            (self.user_data['user_id'].isin(top_similar_user_ids)) & 
            ((self.user_data['purchase'] == 1) | (self.user_data['in_wishlist'] == 1)),
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

    def search_similar_products_by_keyword(self, keyword, page=1, pagesize=10, n=20):
        similar_product_ids = self.find_similar_products(keyword, n, input_type="text")

        if not similar_product_ids:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm tương tự")

        start_index = (page - 1) * pagesize
        end_index = start_index + pagesize

        return similar_product_ids[start_index:end_index]

    def _get_product_embedding_by_id(self, product_id):
        """
        Lấy embedding của một sản phẩm dựa trên ID.
        Nếu embedding đã được cache, lấy từ cache. Nếu không, truy vấn cơ sở dữ liệu.
        Args:
            product_id (int): ID của sản phẩm.

        Returns:
            np.ndarray: Embedding của sản phẩm dưới dạng mảng NumPy, hoặc None nếu không tìm thấy.
        """
        # Kiểm tra trong cache
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