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
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sentence_transformers import SentenceTransformer
from annoy import AnnoyIndex

# Local imports
from entities.base import Product, Category
from utils.redis_utils import get_cached_data, cache_data, delete_key

load_dotenv()

DATABASE_URL = os.getenv("DB_URL")
PRODUCT_EMBEDDINGS_FILE = 'product_embeddings.pkl'
PRODUCTS_DATA_FILE = 'products_data.csv'
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

        # Lazy loading attributes - chỉ khởi tạo khi cần
        self._model = None
        self._products_df = None
        self._product_embeddings = None
        self._user_data = None
        self._user_vectors = None
        self._behavior_matrix = None
        self._annoy_index = None
        
        self._initialized = True

    def _schedule_data_refresh(self):
        """Lên lịch các tác vụ làm mới dữ liệu với khoảng thời gian cụ thể."""
        # Lên lịch refresh dữ liệu sản phẩm và embeddings mỗi ngày
        self.scheduler.add_job(self.refresh_product_data, 'interval', hours=24, id='refresh_product_data')
        # Lên lịch refresh hành vi người dùng mỗi 3 tiếng
        self.scheduler.add_job(self.refresh_user_behavior, 'interval', hours=6, id='refresh_user_behavior')

        # Lắng nghe sự kiện thực thi các tác vụ
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    def _job_listener(self, event):
        if event.exception:
            print(f"Công việc {event.job_id} bị lỗi")
        else:
            print(f"Công việc {event.job_id} hoàn thành thành công")

    def refresh_product_data(self):
        """Làm mới dữ liệu sản phẩm và embeddings của sản phẩm."""
        delete_key('products')
        print(f"Làm mới dữ liệu sản phẩm vào lúc {datetime.datetime.now()}")
        self._products_df = self._load_products_data()  # Tải lại dữ liệu sản phẩm
        cache_data('products', self._products_df)  # Lưu lại vào cache

        # Làm mới embeddings của sản phẩm
        delete_key("product_embeddings")
        self._product_embeddings = self._load_embeddings()  # Tải lại embeddings
        cache_data('product_embeddings', self._product_embeddings)  # Lưu lại vào cache

    def refresh_user_behavior(self):
        """Làm mới dữ liệu hành vi người dùng và cache lại."""
        delete_key("user_data")
        print(f"Làm mới ma trận hành vi người dùng vào lúc {datetime.datetime.now()}")
        self._user_data = self._load_user_data()  # Tải lại dữ liệu hành vi người dùng
        cache_data('user_data', self._user_data)  # Lưu lại vào cache

        delete_key("user_vectors")
        delete_key("behavior_matrix")
        self._user_vectors, self._behavior_matrix = self._compute_user_vectors()
        # Tái cấu trúc cây annoy
        self._annoy_index = None
        self._annoy_index = self._build_annoy_index()
        print("Tái cấu trúc cây annoy")
        cache_data("user_vectors", self._user_vectors)  # Lưu lại user vectors vào cache
        cache_data("behavior_matrix", self._behavior_matrix)  # Lưu lại ma trận hành vi vào cache

    @property
    def model(self):
        if self._model is None:
            self._model = self._load_model()
        return self._model

    @property
    def products_df(self):
        if self._products_df is None:
            self._products_df = self._load_products_data()
        return self._products_df

    @property
    def product_embeddings(self):
        if self._product_embeddings is None:
            self._product_embeddings = self._load_embeddings()
        return self._product_embeddings

    def _load_model(self):
        if os.path.exists(SENTENCE_TRANSFORMER_MODEL_FILE):
            model = joblib.load(SENTENCE_TRANSFORMER_MODEL_FILE)
        else:
            model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            joblib.dump(model, SENTENCE_TRANSFORMER_MODEL_FILE)
        return model

    def _load_products_data(self):
        products_df = get_cached_data('products')
        if products_df is not None:
            return products_df
            
        if os.path.exists(PRODUCTS_DATA_FILE):
            products_df = pd.read_csv(PRODUCTS_DATA_FILE)
        else:
            products_df = self._get_products_from_db()
            products_df.to_csv(PRODUCTS_DATA_FILE, index=False)
            
        cache_data('products', products_df)
        return products_df

    def _load_embeddings(self):
        embeddings = get_cached_data('product_embeddings')
        if embeddings is not None:
            return embeddings
            
        if os.path.exists(PRODUCT_EMBEDDINGS_FILE):
            embeddings = joblib.load(PRODUCT_EMBEDDINGS_FILE)
        else:
            embeddings = self._compute_product_embeddings(self.products_df)
            joblib.dump(embeddings, PRODUCT_EMBEDDINGS_FILE)
            
        cache_data('product_embeddings', embeddings)
        return embeddings

    @lru_cache(maxsize=1)
    def _get_products_from_db(self):
        session = self.Session()
        try:
            results = (
                session.query(Product, Category)
                .join(Category, Product.category_id == Category.id)
                .all()
            )
            print(f"Found {len(results)} results in the query.")
            products_data = [{
                'id': product.id,
                'product_name': product.product_name,
                'price': product.price,
                'sold': product.sold,
                'rating': product.rating,
                'category': category.name,
                'description': product.description
            } for product, category in results]
        finally:
            session.close()
        return pd.DataFrame(products_data)

    @property
    def user_data(self):
        if self._user_data is None:
            self._user_data = self._load_user_data()
        return self._user_data

    def _load_user_data(self):
        user_data = get_cached_data('user_data')
        if user_data is not None:
            return user_data
            
        user_data = self._get_user_behavior_from_db()
        cache_data('user_data', user_data)
        return user_data

    @lru_cache(maxsize=1)
    def _get_user_behavior_from_db(self):
        query = "CALL GetUserBehavior();"
        
        # Sử dụng cursor để thực hiện truy vấn
        with self.engine.connect() as conn:
            cursor = conn.connection.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            cursor.close()

        return pd.DataFrame(result, columns=columns)

        
    def _compute_product_embeddings(self, products_df):
        products_df['combined_features'] = (
            products_df['product_name'] + " " +
            products_df['category'] + " " +
            products_df['description'].fillna('')
        )
        return self.model.encode(products_df['combined_features'].tolist(), convert_to_tensor=False)

    def get_user_vectors(self):
        if self._user_vectors is None or self._behavior_matrix is None:
            vectors, matrix = self._compute_user_vectors()
            self._user_vectors = vectors
            self._behavior_matrix = matrix
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
        print(user_vectors)
        return user_vectors, behavior_matrix

    @property
    def annoy_index(self):
        if self._annoy_index is None:
            self._annoy_index = self._build_annoy_index()
        return self._annoy_index

    def _build_annoy_index(self):
        user_vectors, _ = self.get_user_vectors()
        vector_dim = user_vectors.shape[1]
        index = AnnoyIndex(vector_dim, 'angular')
        for i, vec in enumerate(user_vectors):
            index.add_item(i, vec)
        index.build(10)
        return index

    def find_similar_products(self, input_text, n=10):
        input_embeddings = self.model.encode(input_text, convert_to_tensor=False)
        similarities = cosine_similarity([input_embeddings], self.product_embeddings)[0]
        print("Similarities: ", similarities)
        top_n_indices = np.argsort(similarities)[::-1][:n]
        similar_product_ids = self.products_df.iloc[top_n_indices]['id'].tolist()
        return similar_product_ids

    def recommend_products_for_new_user(self, top_n=18):
        # Đề xuất các sản phẩm phổ biến hoặc sản phẩm bán chạy nhất
        popular_products = self.products_df[['id', 'rating', 'sold']].sort_values(by=['sold', 'rating'], ascending=False)
        return popular_products['id'].head(top_n).tolist()


    def recommend_products_for_user(self, user_id, top_n=18, similar_users_count=10):
        # lấy ma trận hành vi người dùng
        user_vectors, behavior_matrix = self.get_user_vectors()

        if user_id not in self._behavior_matrix.index:
            return self.recommend_products_for_new_user(top_n)
        
        user_idx = behavior_matrix.index.get_loc(user_id)
        
        # Lấy các người dùng tương tự từ Annoy Index
        similar_user_indices = self.annoy_index.get_nns_by_item(user_idx, similar_users_count + 1)[1:]
        similar_user_ids = behavior_matrix.index[similar_user_indices]

        # Lấy danh sách các sản phẩm mà người dùng đã mua
        user_purchases = set(self.user_data.loc[
            (self.user_data['user_id'] == user_id) & (self.user_data['purchase'] == 1),
            'product_id'
        ])

        # Lấy danh sách các sản phẩm mà người dùng tương tự đã mua hoặc có trong wishlist
        similar_user_products = set(self.user_data.loc[
            (self.user_data['user_id'].isin(similar_user_ids)) & 
            ((self.user_data['purchase'] == 1) | (self.user_data['in_wishlist'] == 1)),
            'product_id'
        ])

        recommended_products = similar_user_products - user_purchases

        # Khi không đủ số lượng đề xuất, bổ sung các sản phẩm bán chạy và có rating cao
        if len(recommended_products) < top_n:
            excluded_products = recommended_products | user_purchases
            all_products = self.products_df[~self.products_df['id'].isin(excluded_products)]
            
            # Chỉ sắp xếp theo rating và số lượt mua khi cần thiết
            top_products = all_products[['id', 'rating', 'sold']].sort_values(by=['rating', 'sold'], ascending=False)
            
            recommended_products.update(top_products['id'].head(top_n - len(recommended_products)).tolist())

        return list(recommended_products)[:top_n]


    def search_similar_products_by_keyword(self, keyword, page=1, pagesize=10, n=20):
        similar_product_ids = self.find_similar_products(keyword, n)

        if not similar_product_ids:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm tương tự")

        start_index = (page - 1) * pagesize
        end_index = start_index + pagesize

        return similar_product_ids[start_index:end_index]

    def get_similar_products_by_id(self, product_id: int, n=12):
        product_row = self.products_df[self.products_df['id'] == product_id]

        if product_row.empty:
            raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại")

        input_text = (
            product_row.iloc[0]['product_name'] + " " + 
            product_row.iloc[0]['category'] + " " + 
            (product_row.iloc[0]['description'] or '')
        )
            
        similar_product_ids = self.find_similar_products(input_text, n + 1)
        similar_product_ids = [id_ for id_ in similar_product_ids if id_ != product_id]

        if not similar_product_ids:
            raise HTTPException(status_code=404, detail="Không tìm thấy sản phẩm tương tự")

        return similar_product_ids[:n]