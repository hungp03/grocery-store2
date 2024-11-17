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
    embedding = Column(LargeBinary)
    category = relationship("Category", back_populates="products")

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    products = relationship("Product", back_populates="category")

