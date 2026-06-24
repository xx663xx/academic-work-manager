from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import get_students, get_teachers, init_db


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
            {"label": "Импорт студентов", "url": "/admin/import/students"},
            {"label": "Импорт преподавателей", "url": "/admin/import/teachers"},
            {"label": "Просмотр студентов", "url": "/admin/students"},
            {"label": "Просмотр преподавателей", "url": "/admin/teachers"},
            {"label": "Просмотр всех тем"},
            {"label": "Управление назначениями"},
            {"label": "Изменение темы или руководителя"},
            {"label": "Настройка сроков и блокировок"},
            {"label": "Экспорт результата в Excel"},
        ],
    },
    "teacher": {
        "title": "Панель преподавателя",
        "description": "Преподаватель вносит темы и подтверждает или отклоняет заявки студентов.",
        "actions": [
            {"label": "Добавление темы"},
            {"label": "Редактирование своей темы"},
            {"label": "Просмотр тем преподавателя"},
            {"label": "Просмотр заявок студентов"},
            {"label": "Подтверждение темы"},
            {"label": "Отказ по заявке студента"},
        ],
    },
    "student": {
        "title": "Панель студента",
        "description": "Студент выбирает доступную тему и отслеживает статус согласования.",
        "actions": [
            {"label": "Просмотр доступных тем"},
            {"label": "Выбор темы до подтверждения"},
            {"label": "Просмотр своей темы и руководителя"},
            {"label": "Просмотр статуса согласования"},
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


@app.get("/admin/students")
async def admin_students(request: Request):
    init_db()
    return templates.TemplateResponse(
        request,
        "reference_list.html",
        {
            "title": "Студенты",
            "description": "Справочник студентов, загруженных для распределения тем.",
            "empty_message": "Студенты еще не загружены.",
            "columns": [
                ("full_name", "ФИО"),
                ("study_group", "Группа"),
                ("course", "Курс"),
                ("login", "Логин"),
                ("contact", "Контакт"),
            ],
            "rows": get_students(),
            "back_url": "/admin",
        },
    )


@app.get("/admin/teachers")
async def admin_teachers(request: Request):
    init_db()
    return templates.TemplateResponse(
        request,
        "reference_list.html",
        {
            "title": "Преподаватели",
            "description": "Справочник преподавателей, которые могут предлагать темы.",
            "empty_message": "Преподаватели еще не загружены.",
            "columns": [
                ("full_name", "ФИО"),
                ("position", "Должность"),
                ("academic_degree", "Ученая степень"),
                ("academic_title", "Ученое звание"),
                ("specialization", "Направление"),
                ("contact", "Контакт"),
            ],
            "rows": get_teachers(),
            "back_url": "/admin",
        },
    )


@app.get("/admin/import/students")
async def admin_import_students(request: Request):
    return templates.TemplateResponse(
        request,
        "import_form.html",
        {
            "title": "Импорт студентов",
            "description": "Загрузка справочника студентов из Excel-файла.",
            "columns": ["ФИО", "Группа", "Курс", "Логин", "Контакт"],
            "sample_path": "samples/students.xlsx",
            "back_url": "/admin",
        },
    )


@app.get("/admin/import/teachers")
async def admin_import_teachers(request: Request):
    return templates.TemplateResponse(
        request,
        "import_form.html",
        {
            "title": "Импорт преподавателей",
            "description": "Загрузка справочника преподавателей из Excel-файла.",
            "columns": [
                "ФИО",
                "Должность",
                "Ученая степень",
                "Ученое звание",
                "Направление",
                "Контакт",
            ],
            "sample_path": "samples/teachers.xlsx",
            "note": "Ученая степень и ученое звание могут быть пустыми. Должность и ФИО обязательны.",
            "back_url": "/admin",
        },
    )


@app.get("/teacher")
async def teacher_dashboard(request: Request):
    return render_dashboard(request, "teacher")


@app.get("/student")
async def student_dashboard(request: Request):
    return render_dashboard(request, "student")
