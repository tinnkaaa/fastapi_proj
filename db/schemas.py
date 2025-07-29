from pydantic import BaseModel
from typing import Optional, List

class BookBase(BaseModel):
    name: str
    description: str
    pages: int
    img: Optional[str] = None
    category_id: Optional[int] = None
    author_id: int
    owner_id: int

class BookCreate(BookBase):
    pass

class AuthorBase(BaseModel):
    first_name: str
    last_name: str
    bio: Optional[str] = None

class AuthorCreate(AuthorBase):
    pass

class Author(AuthorBase):
    id: int

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str
    email: str

class User(UserBase):
    id: int
    is_active: bool = True

    class Config:
        from_attributes = True

class UserCreate(UserBase):
    password: str

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int

    class Config:
        from_attributes = True

class Book(BookBase):
    id: int
    author: Author
    category: Optional[Category] = None
