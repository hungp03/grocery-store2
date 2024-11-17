from sqlalchemy import Column, Integer, String, Float, ForeignKey, LargeBinary, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import joblib
import pandas as pd

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

def compute_product_embeddings(products_df):
    """
    Tính toán embedding cho tất cả sản phẩm trong DataFrame.
    """

    products_df['combined_features'] = (
        products_df['product_name'] + " " +
        products_df['category'] + " " +
        products_df['description'].fillna('')
    )
    
    embeddings = model.encode(products_df['combined_features'].tolist(), convert_to_tensor=False)
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
