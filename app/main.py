from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Academic Work Manager")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=BASE_DIR / "templates")


ROLES = [
    {
        "key": "admin",
        "title": "Администратор",
        "description": "Импортирует данные, назначает темы и выгружает результат.",
    },
    {
        "key": "teacher",
        "title": "Преподаватель",
        "description": "Просматривает своих студентов и подтверждает темы.",
    },
    {
        "key": "student",
        "title": "Студент",
        "description": "Смотрит свое назначение и статус темы.",
    },
]


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "roles": [role["title"] for role in ROLES],
            "next_steps": [
                "подключить SQLite",
                "добавить импорт студентов",
                "добавить импорт преподавателей",
                "сделать назначение темы",
            ],
        },
    )


@app.get("/login")
async def login(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "roles": ROLES,
        },
    )
