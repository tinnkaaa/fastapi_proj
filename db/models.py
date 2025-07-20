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

    category = Column(String(20), nullable=True)

    author_id = Column(Integer, ForeignKey("authors.id"))
    author = relationship("Author", back_populates="books")

class Author(Base):
    __tablename__ = "authors"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(20))
    last_name = Column(String(20))
    bio = Column(String(255), nullable=True)

    books = relationship("Book", back_populates="author")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20), unique=True, nullable=False)
    email = Column(String(20), unique=True, nullable=True)
    password = Column(String(20), nullable=False)    