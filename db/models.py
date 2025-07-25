from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .engine import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), unique=True)
    description = Column(String(255))
    pages = Column(Integer)
    img = Column(String, nullable=True)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category_rel = relationship("Category", back_populates="books")

    author_id = Column(Integer, ForeignKey("authors.id"))
    author = relationship("Author", back_populates="books")

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="books")


class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(20))
    last_name = Column(String(20))
    bio = Column(String(255), nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="authors")

    books = relationship("Book", back_populates="author")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20), unique=True, nullable=False)
    email = Column(String(20), unique=True, nullable=True)
    password = Column(String(20), nullable=False)  
    books = relationship("Book", back_populates="owner")   
    authors = relationship("Author", back_populates="owner")
    categories = relationship("Category", back_populates="owner")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="categories")

    books = relationship("Book", back_populates="category_rel")