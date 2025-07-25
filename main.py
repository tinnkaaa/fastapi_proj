from datetime import datetime, timedelta
from typing import Annotated, Optional
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response, status, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt

from db import schemas, crud, models
from db.engine import session_local, create_db

app = FastAPI(title="Books Library API", version="1.0.0")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
create_db()

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["sha256_crypt", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()

def create_token(data: dict):
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        return payload
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def get_current_user(token: Optional[str] = Cookie(None), db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(token)
    username = payload.get("sub")
    user = crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def parse_int(value: str = Form("")) -> Optional[int]:
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="category_id має бути числом або порожнім")


@app.get("/books", response_class=HTMLResponse)
def all_books(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    books = db.query(models.Book).filter(models.Book.owner_id == current_user.id).all()
    return templates.TemplateResponse("all_books.html", {"request": request, "books": books})

@app.get("/books/create", response_class=HTMLResponse)
def create_book_form(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    categories = crud.get_categories_by_owner(db, owner_id=current_user.id)
    authors = crud.get_authors_by_owner(db, owner_id=current_user.id)
    return templates.TemplateResponse("create_books.html", {"request": request, "categories": categories, "authors": authors})

@app.post("/books/create", response_class=HTMLResponse)
def create_book_post(
    request: Request,
    name: str = Form(...),
    author: str = Form(...),
    pages: int = Form(...),
    category: str = Form(...),
    img: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    context = {"request": request}

    existing_book = db.query(models.Book).filter(
        models.Book.name == name,
        models.Book.owner_id == current_user.id
    ).first()

    if existing_book:
        context["error"] = f"Книга з назвою '{name}' вже існує"
        context["categories"] = crud.get_categories_by_owner(db, owner_id=current_user.id)
        context["authors"] = crud.get_authors_by_owner(db, owner_id=current_user.id)
        return templates.TemplateResponse("create_books.html", context)

    author_obj = db.query(models.Author).filter(
        (models.Author.first_name + " " + models.Author.last_name) == author,
        models.Author.owner_id == current_user.id
    ).first()
    if not author_obj:
        context["error"] = "Автор не знайдений"
        context["categories"] = crud.get_categories_by_owner(db, owner_id=current_user.id)
        context["authors"] = crud.get_authors_by_owner(db, owner_id=current_user.id)
        return templates.TemplateResponse("create_books.html", context)

    category_obj = db.query(models.Category).filter(
        models.Category.name == category,
        models.Category.owner_id == current_user.id
    ).first()
    if not category_obj:
        context["error"] = "Категорія не знайдена"
        context["categories"] = crud.get_categories_by_owner(db, owner_id=current_user.id)
        context["authors"] = crud.get_authors_by_owner(db, owner_id=current_user.id)
        return templates.TemplateResponse("create_books.html", context)

    try:
        new_book = models.Book(
            name=name,
            author_id=author_obj.id,
            pages=pages,
            category_id=category_obj.id,
            img=img,
            owner_id=current_user.id
        )
        db.add(new_book)
        db.commit()
        db.refresh(new_book)
        context["success"] = "Книгу успішно додано!"
    except Exception as e:
        db.rollback()
        context["error"] = f"Помилка при створенні книги: {str(e)}"

    context["categories"] = crud.get_categories_by_owner(db, owner_id=current_user.id)
    context["authors"] = crud.get_authors_by_owner(db, owner_id=current_user.id)

    return templates.TemplateResponse("create_books.html", context)

@app.get("/books/update/{book_id}", response_class=HTMLResponse)
def update_book_form(book_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    book = db.query(models.Book).filter(models.Book.id == book_id, models.Book.owner_id == current_user.id).first()
    if not book:
        return templates.TemplateResponse("update_book.html", {"request": request, "error": "Книга не знайдена"})
    authors = db.query(models.Author).filter(models.Author.owner_id == current_user.id).all()
    categories = db.query(models.Category).filter(models.Category.owner_id == current_user.id).all()
    return templates.TemplateResponse("update_book.html", {
        "request": request,
        "book": book,
        "authors": authors,
        "categories": categories,
    })

@app.post("/books/update/{book_id}", response_class=HTMLResponse)
def update_book_post(
    book_id: int,
    request: Request,
    name: str = Form(...),
    author_id: int = Form(...),
    pages: int = Form(...),
    category_id: Optional[int] = Depends(parse_int),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    book = db.query(models.Book).filter(models.Book.id == book_id, models.Book.owner_id == current_user.id).first()
    if not book:
        return templates.TemplateResponse("update_book.html", {"request": request, "error": "Книга не знайдена"})
    
    author = db.query(models.Author).filter(models.Author.id == author_id, models.Author.owner_id == current_user.id).first()
    if not author:
        return templates.TemplateResponse("update_book.html", {"request": request, "error": "Автор не знайдений"})

    if category_id is not None:
        category = db.query(models.Category).filter(models.Category.id == category_id, models.Category.owner_id == current_user.id).first()
        if not category:
            return templates.TemplateResponse("update_book.html", {"request": request, "error": "Категорія не знайдена"})

    book.name = name
    book.author_id = author_id
    book.pages = pages
    book.category_id = category_id

    db.commit()
    db.refresh(book)

    authors = db.query(models.Author).filter(models.Author.owner_id == current_user.id).all()
    categories = db.query(models.Category).filter(models.Category.owner_id == current_user.id).all()

    return templates.TemplateResponse("update_book.html", {
        "request": request,
        "book": book,
        "authors": authors,
        "categories": categories,
        "success": "Книга успішно оновлена"
    })
@app.get("/books/delete", response_class=HTMLResponse)
def delete_book(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    books = db.query(models.Book).filter(models.Book.owner_id == current_user.id).all()
    return templates.TemplateResponse("delete_book.html", {"request": request, "books": books})

@app.post("/books/delete/{book_id}", response_class=HTMLResponse)
def delete_book_post(book_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    context = {"request": request}
    book = db.query(models.Book).filter(models.Book.id == book_id, models.Book.owner_id == current_user.id).first()
    if not book:
        context["error"] = "Книга не знайдена"
        return templates.TemplateResponse("delete_book.html", context)
    crud.delete_book(db, book.id)
    context["success"] = f"Книга '{book.name}' успішно видалена"
    return templates.TemplateResponse("delete_book.html", context)

@app.get("/authors", response_class=HTMLResponse)
def all_authors(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    authors = crud.get_authors_by_owner(db, owner_id=current_user.id)
    return templates.TemplateResponse("all_authors.html", {"request": request, "authors": authors})

@app.get("/authors/create", response_class=HTMLResponse)
def create_author_form(request: Request):
    return templates.TemplateResponse("create_author.html", {"request": request})

@app.post("/authors/create", response_class=HTMLResponse)
def create_author_post(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    bio: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    context = {"request": request}
    if not first_name or not last_name:
        context["error"] = "Будь ласка, заповніть всі поля"
        return templates.TemplateResponse("create_author.html", context)
    author_data = schemas.AuthorCreate(first_name=first_name, last_name=last_name, bio=bio)
    crud.create_author(db, author_data, owner_id=current_user.id)
    context["success"] = "Автор успішно доданий!"
    return templates.TemplateResponse("create_author.html", context)

@app.get("/authors/{author_id}/books", response_class=HTMLResponse)
def books_by_author(
    request: Request,
    author_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    author = db.query(models.Author).filter(models.Author.id == author_id, models.Author.owner_id == current_user.id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Автор не знайдений")
    books = crud.by_author(db, author_id, owner_id=current_user.id)
    return templates.TemplateResponse("author_books.html", {"request": request, "books": books, "author": author})

@app.get("/categories", response_class=HTMLResponse)
def all_categories(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    categories = crud.get_categories_by_owner(db, owner_id=current_user.id)
    return templates.TemplateResponse("all_categories.html", {"request": request, "categories": categories})

@app.get("/categories/create", response_class=HTMLResponse)
def create_category_form(request: Request):
    return templates.TemplateResponse("create_category.html", {"request": request})

@app.post("/categories/create", response_class=HTMLResponse)
def create_category_post(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    context = {"request": request}
    if not name:
        context["error"] = "Будь ласка, введіть назву категорії"
        return templates.TemplateResponse("create_category.html", context)
    category_data = schemas.CategoryCreate(name=name)
    crud.create_category(db, category_data, owner_id=current_user.id)
    context["success"] = "Категорію успішно додано!"
    return templates.TemplateResponse("create_category.html", context)

@app.get("/categories/{category_id}/books", response_class=HTMLResponse)
def books_by_category(
    request: Request,
    category_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    category = db.query(models.Category).filter(models.Category.id == category_id, models.Category.owner_id == current_user.id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Категорія не знайдена")
    books = crud.by_category(db, category_id=category_id, owner_id=current_user.id)
    return templates.TemplateResponse("category_books.html", {"request": request, "books": books, "category": category})

@app.post("/token")
async def get_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    user_data = crud.get_user(db, form_data.username)
    if not user_data or not pwd_context.verify(form_data.password, user_data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_token({"sub": user_data.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db, user)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_user(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...),
):
    user_data = crud.get_user(db, username)
    if not user_data or not pwd_context.verify(password, user_data.password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неправильні дані"}, status_code=401)
    token = create_token({"sub": user_data.username})
    response = RedirectResponse(url="/books", status_code=302)
    response.set_cookie("token", token, httponly=True)
    return response

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    context = {"request": request}
    existing_user = crud.get_user(db, username)
    if existing_user:
        context["error"] = "Користувач з таким ім'ям вже існує"
        return templates.TemplateResponse("register.html", context)
    new_user = crud.create_user(db, schemas.UserCreate(username=username, email=email, password=password))
    token = create_token({"sub": new_user.username})
    response = RedirectResponse(url="/books", status_code=302)
    response.set_cookie("token", token, httponly=True)
    return response

@app.post("/logout")
def logout(response: Response):
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("token")
    return response