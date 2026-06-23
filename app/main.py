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

DASHBOARDS = {
    "admin": {
        "title": "Панель администратора",
        "description": "Администратор имеет полный доступ к данным, настройкам и всем назначениям.",
        "actions": [
            "Импорт студентов",
            "Импорт преподавателей",
            "Просмотр всех тем",
            "Просмотр студентов",
            "Просмотр преподавателей",
            "Управление назначениями",
            "Изменение темы или руководителя",
            "Настройка сроков и блокировок",
            "Экспорт результата в Excel",
        ],
    },
    "teacher": {
        "title": "Панель преподавателя",
        "description": "Преподаватель вносит темы и подтверждает или отклоняет заявки студентов.",
        "actions": [
            "Добавление темы",
            "Редактирование своей темы",
            "Просмотр тем преподавателя",
            "Просмотр заявок студентов",
            "Подтверждение темы",
            "Отказ по заявке студента",
        ],
    },
    "student": {
        "title": "Панель студента",
        "description": "Студент выбирает доступную тему и отслеживает статус согласования.",
        "actions": [
            "Просмотр доступных тем",
            "Выбор темы до подтверждения",
            "Просмотр своей темы и руководителя",
            "Просмотр статуса согласования",
        ],
    },
}


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


def render_dashboard(request: Request, role_key: str):
    dashboard = DASHBOARDS[role_key]
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "dashboard": dashboard,
            "roles": [role["title"] for role in ROLES],
        },
    )


@app.get("/admin")
async def admin_dashboard(request: Request):
    return render_dashboard(request, "admin")


@app.get("/teacher")
async def teacher_dashboard(request: Request):
    return render_dashboard(request, "teacher")


@app.get("/student")
async def student_dashboard(request: Request):
    return render_dashboard(request, "student")
