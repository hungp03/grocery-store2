from sqlalchemy import Column, Integer, String, Float, ForeignKey, LargeBinary, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import joblib
import pandas as pd
from nltk.tokenize import word_tokenize
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
STOPWORDS_VIETNAMESE = set([
    "cái", "đây", "là", "và", "có", "cũng", "trong", "của", "một", "này", "khi", "được",
    "với", "như", "bởi", "không", "là", "nếu", "vì", "sẽ", "cũng", "mà", "hơn", "các", "từ",
    "nói", "về", "mới", "tại", "của", "đến", "thì", "mà", "cho", "bằng", "và", "lại", "những",
    "vậy", "vẫn", "đang", "ai", "khi", "đó", "sẽ", "có", "chỉ", "các", "với", "mà", "hay", "trong",
    "nếu", "nào", "nhiều", "thế", "sẽ", "bởi", "về", "được", "mình", "rồi", "nữa", "là", "thấy",
    "ra", "thì", "mỗi", "vì", "sao", "tất", "thế", "nơi", "giữa", "sau", "khi", "tất cả", "đó",
    "cũng", "bởi", "một", "thế", "cả", "vào", "sử dụng", "có", "đi", "được", "nhưng", "lại", "làm",
    "vào", "khiến", "đến", "nó", "lớn", "tính", "trong", "không", "đưa", "vào", "trải", "cùng",
    "bất", "sẽ", "giống", "trải", "hơn", "mới", "chỉ", "thực", "đã", "ngày", "với", "lại", "điều",
    "đều", "cho", "chưa", "tại", "người", "tôi", "của", "thực", "trong", "thấy", "được", "cũng",
    "rất", "mà", "là", "sự", "nếu", "nào", "để", "thực", "chỉ", "người", "bởi", "vì", "sự",
    "hầu", "nói", "mình", "chưa", "rất", "với", "tất", "bạn", "gì", "cái", "các", "sao", "trực",
    "người", "theo", "có", "vậy", "thể", "sẽ", "dùng", "có thể", "và", "chẳng", "như", "làm",
    "vào", "hơn", "bằng", "chúng", "cái", "về", "sau", "lấy", "không", "từ", "mới", "chỉ", "được",
    "sẽ", "ngay", "về", "và", "từ", "nào", "nhưng", "của", "một", "với", "thế", "trong", "có",
    "thực", "hơn", "cần", "tìm", "để", "đi", "khi", "tương", "đặc", "nghĩa", "tăng", "thực",
    "bằng", "thế", "nghe", "bởi", "này", "không", "thành", "mà", "chúng", "giữa", "có", "sử",
    "người", "đó", "những", "cần", "gì", "làm", "sẽ", "vào", "vậy", "nếu", "vì", "rồi", "vào",
    "cũng", "từ", "sao", "khi", "rất", "mà", "nên", "tự", "khá", "được", "và", "ngày", "hoặc",
    "chứ", "để", "mà", "chúng", "thêm", "cũng", "sao", "gì", "tất", "không", "nói", "bạn"
])


DATABASE_URL = "mysql+mysqlconnector://root:123456@localhost/webnongsan"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    product_name = Column(String)
    price = Column(Float)
    sold = Column(Integer)
    rating = Column(Float)
    image_url = Column(String)
    category_id = Column(Integer, ForeignKey('categories.id'))
    description = Column(String)
    embedding = Column(LargeBinary)
    category = relationship("Category", back_populates="products")

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    
    products = relationship("Product", back_populates="category")

SENTENCE_TRANSFORMER_MODEL_FILE = 'sentence_transformer_model.pkl'
model = joblib.load(SENTENCE_TRANSFORMER_MODEL_FILE)


def remove_stopwords(text):
    """Loại bỏ stopwords từ văn bản"""
    words = word_tokenize(text)
    filtered_words = [word for word in words if word.lower() not in STOPWORDS_VIETNAMESE]
    return ' '.join(filtered_words)

def compute_product_embeddings(products_df):
    """
    Tính toán embedding cho tất cả sản phẩm trong DataFrame.
    """

    products_df['combined_features'] = (
        products_df['product_name'] + " " +
        products_df['category'] + " " +
        products_df['description'].fillna('')
    )

    # Loại bỏ stopwords từ các đặc tính sản phẩm
    products_df['cleaned_features'] = products_df['combined_features'].apply(remove_stopwords)
    
    embeddings = model.encode(products_df['cleaned_features'].tolist(), convert_to_tensor=False)
    return embeddings

def update_product_embeddings():
    # Hàm cập nhật tất cả embedding của sản phẩm vào cơ sở dữ liệu.
    session = Session()
    
    try:
        products = session.query(Product).all()
        print(f"Found {len(products)} products in the database.")

        if not products:
            print("No products found. Exiting...")
            return
        
        # Chuẩn bị dữ liệu sản phẩm
        products_data = [{
            'id': product.id,
            'product_name': product.product_name,
            'category': product.category.name if product.category else 'No Category',
            'description': product.description
        } for product in products]
        
        products_df = pd.DataFrame(products_data)
        
        embeddings = compute_product_embeddings(products_df)
        print(f"Generated {len(embeddings)} embeddings.")
        
        for i, product in enumerate(products):
            embedding = embeddings[i]
            print(f"Updating embedding for product ID: {product.id}")
            product.embedding = embedding.tobytes()

        session.commit()
        print("Embeddings updated successfully.")
    
    except Exception as e:
        session.rollback()
        print(f"An error occurred: {e}")
    
    finally:
        session.close()


if __name__ == "__main__":
    update_product_embeddings()
