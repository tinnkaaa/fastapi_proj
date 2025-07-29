from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from db import models, schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_book(db: Session, book: schemas.BookCreate):
    author = db.query(models.Author).filter(models.Author.id == book.author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    new_book = models.Book(
        name=book.name,
        description=book.description,
        pages=book.pages,
        img=book.img,
        author_id=book.author_id,
        category_id=book.category_id,
        owner_id=book.owner_id
    )
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book

def get_books(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.Book).offset(skip).limit(limit).all()

def delete_book(db: Session, book_id: int):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return book

def update_book(db: Session, book_id: int, updated_data: schemas.BookCreate):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.name = updated_data.name
    book.description = updated_data.description
    book.pages = updated_data.pages
    book.img = updated_data.img
    book.category_id = updated_data.category_id
    book.author_id = updated_data.author_id

    db.commit()
    db.refresh(book)
    return book

def by_category(db: Session, category_id: int, owner_id: int = None):
    query = db.query(models.Book).filter(models.Book.category_id == category_id)
    if owner_id is not None:
        query = query.filter(models.Book.owner_id == owner_id)
    books = query.all()
    if not books:
        raise HTTPException(status_code=404, detail="No books found in this category")
    return books

def by_author(db: Session, author_id: int, owner_id: int | None = None):
    query = db.query(models.Book).filter(models.Book.author_id == author_id)
    if owner_id is not None:
        query = query.filter(models.Book.owner_id == owner_id)
    books = query.all()
    if not books:
        raise HTTPException(status_code=404, detail="No books found for this author")
    return books

def create_author(db: Session, author: schemas.AuthorCreate, owner_id: int):
    new_author = models.Author(**author.model_dump(), owner_id=owner_id)
    db.add(new_author)
    db.commit()
    db.refresh(new_author)
    return new_author

def get_authors(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.Author).offset(skip).limit(limit).all()

def delete_author(db: Session, author_id: int):
    author = db.query(models.Author).filter(models.Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    db.delete(author)
    db.commit()
    return author

def update_author(db: Session, author_id: int, updated_data: schemas.AuthorCreate):
    author = db.query(models.Author).filter(models.Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    author.first_name = updated_data.first_name
    author.last_name = updated_data.last_name
    author.bio = updated_data.bio

    db.commit()
    db.refresh(author)
    return author


def get_user(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        username=user.username,
        email=user.email,
        password=pwd_context.hash(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return user

def get_author_id_by_name(db: Session, author_name: str) -> int | None:
    author = db.query(models.Author).filter(
        (models.Author.first_name + ' ' + models.Author.last_name) == author_name
    ).first()
    if author:
        return author.id
    return None

def get_authors_by_owner(db: Session, owner_id: int):
    return db.query(models.Author).filter(models.Author.owner_id == owner_id).all()

def create_category(db: Session, category: schemas.CategoryCreate, owner_id: int):
    new_category = models.Category(**category.model_dump(), owner_id=owner_id)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

def get_categories_by_owner(db: Session, owner_id: int):
    return db.query(models.Category).filter(models.Category.owner_id == owner_id).all()