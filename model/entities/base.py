from sqlalchemy import Column, Integer, String, Float, ForeignKey, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

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
    category = relationship("Category", back_populates="products")
    embeddings = relationship("ProductEmbedding", back_populates="product", cascade="all, delete-orphan")

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    products = relationship("Product", back_populates="category")

class ProductEmbedding(Base):
    __tablename__ = 'product_embeddings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    embedding = Column(LargeBinary, nullable=False)  # Lưu embedding dưới dạng dữ liệu nhị phân

    product = relationship("Product", back_populates="embeddings")

    def __repr__(self):
        return f"<ProductEmbedding(id={self.id}, product_id={self.product_id})>"
