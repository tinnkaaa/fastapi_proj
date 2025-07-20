from datetime import datetime, timedelta
from typing import Annotated
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi import Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from db import schemas, crud, models
from db.engine import session_local, create_db
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt

app = FastAPI(title="Books Library API", version="1.0.0")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
create_db()

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Підтримка обох схем для сумісності
pwd_context = CryptContext(schemes=["sha256_crypt", "bcrypt"], deprecated="auto")

# Схема для отримання токену
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    '''Отримуємо сесію бази даних'''
    db = session_local()
    try:
        yield db
    finally:
        db.close()

def create_token(data: dict):
    '''Створюємо токен'''
    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode = data.copy()
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    '''Перевіряємо токен'''
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username =  payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        return payload
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def get_current_user(token: str = Cookie(None), db: Session = Depends(get_db)):
    '''Отримуємо поточного користувача з cookie'''
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(token)
    username = payload.get("sub")
    user = crud.get_user(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.get("/books", response_class=HTMLResponse)
def all_books(request: Request, db: Session = Depends(get_db)):
    books = crud.get_books(db)
    return templates.TemplateResponse("all_books.html", context={"request": request, "books": books})

@app.get("/books/create", response_class=HTMLResponse)
def create_book(request: Request, current_user: models.User = Depends(get_current_user)):
    return templates.TemplateResponse("create_books.html", {"request": request})

@app.get("/books/update", response_class=HTMLResponse)
def update_book(request: Request, current_user: models.User = Depends(get_current_user)):
    return templates.TemplateResponse("update_book.html", {"request": request})

@app.post("/books/update", response_class=HTMLResponse)
def update_book_post(
    request: Request,
    name: str = Form(...),
    author: str = Form(...),
    pages: int = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):

    book = db.query(models.Book).filter(models.Book.name == name).first()
    if not book:
        return templates.TemplateResponse("update_book.html", {"request": request, "error": "Книга не знайдена"})

    book.author_id = crud.get_author_id_by_name(db, author) 
    book.pages = pages
    book.category = category

    db.commit()
    db.refresh(book)

    return templates.TemplateResponse("update_book.html", {"request": request, "success": "Книга успішно оновлена"})

@app.api_route("/books/delete", methods=["GET", "POST"], response_class=HTMLResponse)
def delete_book(request: Request,
                name: str = Form(None),
                db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_user)):

    context = {"request": request}

    if request.method == "POST":
        if not name:
            context["error"] = "Введіть назву книги"
            return templates.TemplateResponse("delete_book.html", context)

        book = db.query(models.Book).filter(models.Book.name == name).first()

        if not book:
            context["error"] = f"Книгу з назвою '{name}' не знайдено"
            return templates.TemplateResponse("delete_book.html", context)

        crud.delete_book(db, book.id)
        context["success"] = f"Книга '{name}' успішно видалена"

    return templates.TemplateResponse("delete_book.html", context)

@app.get("/books/by_author", response_class=HTMLResponse)
def books_by_author(request: Request, author_id: int = 0, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    books = {}
    if author_id:
        try:
            books_list = crud.by_author(db, author_id)
            books = {book.name: book for book in books_list}
        except HTTPException:
            books = {}
    return templates.TemplateResponse("author_books.html", {"request": request, "books": books, "author_id": author_id})

@app.get("/books/by_category", response_class=HTMLResponse)
def books_by_category(request: Request, category: str = "", db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    books = {}
    if category:
        books_list = crud.by_category(db, category)
        books = {book.name: book for book in books_list}
    return templates.TemplateResponse("category_books.html", {"request": request, "books": books, "category": category})


@app.api_route("/authors/create", methods=["GET", "POST"], response_class=HTMLResponse)
def create_author(request: Request,
                  first_name: str = Form(...),
                  last_name: str = Form(...),
                  bio: str = Form(""),
                  db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_user)):
    
    context = {"request": request}

    if request.method == "POST":
        if not first_name or not last_name:
            context["error"] = "Будь ласка, заповніть всі поля"
            return templates.TemplateResponse("create_author.html", context)

        author_data = schemas.AuthorCreate(
            first_name=first_name,
            last_name=last_name,
            bio=bio
        )

        crud.create_author(db, author_data)
        context["success"] = "Автор успішно створений"

    return templates.TemplateResponse("create_author.html", context)

@app.get("/authors")
def all_authors(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    '''Отримуємо всіх авторів'''
    authors = crud.get_authors(db)
    return authors


@app.post("/token")
async def get_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Session = Depends(get_db)):
    '''Отримуємо токен'''
    user_data = crud.get_user(db, form_data.username)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    if not pwd_context.verify(form_data.password, user_data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    
    access_token = create_token({"sub": user_data.username})    
    # Повертаємо токен як JSON для OAuth2PasswordBearer
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users")
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    '''Створюємо користувача'''
    return crud.create_user(db, user)

from fastapi.responses import RedirectResponse
from fastapi import Form

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login_user(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...)
):
    user_data = crud.get_user(db, username)
    if not user_data or not pwd_context.verify(password, user_data.password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неправильні дані"}, status_code=401)

    token = create_token({"sub": user_data.username})
    response = RedirectResponse(url="/books", status_code=302)
    response.set_cookie("token", token, httponly=True)
    return response
