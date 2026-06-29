from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import Request, UploadFile
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parents[1]
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
        "status": (
            "Раздел администратора подключен к базе данных. Доступны импорт студентов "
            "и преподавателей, просмотр справочников, создание назначений, список "
            "назначений и Excel-выгрузка результата."
        ),
        "actions": [
            {"label": "Импорт студентов", "url": "/admin/import/students"},
            {"label": "Импорт преподавателей", "url": "/admin/import/teachers"},
            {"label": "Просмотр студентов", "url": "/admin/students"},
            {"label": "Просмотр преподавателей", "url": "/admin/teachers"},
            {"label": "Просмотр назначений", "url": "/admin/assignments"},
            {"label": "Назначить тему студенту", "url": "/admin/assignments/new"},
            {"label": "Изменение темы или руководителя"},
            {"label": "Настройка сроков и блокировок"},
            {"label": "Экспорт результата в Excel", "url": "/admin/assignments"},
        ],
    },
    "teacher": {
        "title": "Панель преподавателя",
        "description": "Преподаватель вносит темы и подтверждает или отклоняет заявки студентов.",
        "status": (
            "Раздел преподавателя подключен к данным, преподаватель может добавлять "
            "темы, видеть свои темы, просматривать заявки студентов и подтверждать "
            "или отклонять выбор темы."
        ),
        "actions": [
            {"label": "Добавление темы", "url": "/teacher/topics"},
            {"label": "Редактирование своей темы"},
            {"label": "Просмотр тем преподавателя", "url": "/teacher/topics"},
            {"label": "Просмотр заявок студентов", "url": "/teacher/requests"},
            {"label": "Подтверждение темы", "url": "/teacher/requests"},
            {"label": "Отказ по заявке студента", "url": "/teacher/requests"},
        ],
    },
    "student": {
        "title": "Панель студента",
        "description": "Студент выбирает доступную тему и отслеживает статус согласования.",
        "status": (
            "Раздел студента работает с реальными темами: студент видит подходящие "
            "темы по курсу, отправляет выбранную тему на подтверждение и смотрит "
            "свое текущее назначение."
        ),
        "actions": [
            {"label": "Просмотр доступных тем", "url": "/student/topics"},
            {"label": "Выбор темы до подтверждения", "url": "/student/topics"},
            {"label": "Просмотр своей темы и руководителя", "url": "/student/assignment"},
            {"label": "Просмотр статуса согласования", "url": "/student/assignment"},
        ],
    },
}

ADMIN_NAVIGATION = [
    {"key": "admin", "label": "Админ", "url": "/admin"},
    {"key": "students", "label": "Студенты", "url": "/admin/students"},
    {"key": "teachers", "label": "Преподаватели", "url": "/admin/teachers"},
    {"key": "assignments", "label": "Назначения", "url": "/admin/assignments"},
]

TEACHER_NAVIGATION = [
    {"key": "topics", "label": "Мои темы", "url": "/teacher/topics"},
    {"key": "requests", "label": "Заявки студентов", "url": "/teacher/requests"},
]

STUDENT_NAVIGATION = [
    {"key": "topics", "label": "Доступные темы", "url": "/student/topics"},
    {"key": "assignment", "label": "Моя тема", "url": "/student/assignment"},
]


def role_titles() -> list[str]:
    return [role["title"] for role in ROLES]


def get_admin_layout_context(active_admin_nav: str) -> dict:
    return {
        "admin_section": True,
        "admin_navigation": ADMIN_NAVIGATION,
        "active_admin_nav": active_admin_nav,
    }


def get_teacher_layout_context(active_teacher_nav: str) -> dict:
    return {
        "teacher_section": True,
        "teacher_navigation": TEACHER_NAVIGATION,
        "active_teacher_nav": active_teacher_nav,
    }


def get_student_layout_context(
    active_student_nav: str,
    selected_student_id: int | None = None,
) -> dict:
    student_navigation = STUDENT_NAVIGATION
    if selected_student_id is not None:
        student_navigation = [
            {
                **item,
                "url": f"{item['url']}?student_id={selected_student_id}",
            }
            for item in STUDENT_NAVIGATION
        ]

    return {
        "student_section": True,
        "student_navigation": student_navigation,
        "active_student_nav": active_student_nav,
    }


def render_dashboard(request: Request, role_key: str):
    dashboard = DASHBOARDS[role_key]
    context = {
        "dashboard": dashboard,
        "roles": role_titles(),
    }
    if role_key == "admin":
        context.update(get_admin_layout_context("admin"))
    if role_key == "teacher":
        context.update(get_teacher_layout_context("topics"))
    if role_key == "student":
        context.update(get_student_layout_context("topics"))

    return templates.TemplateResponse(
        request,
        "index.html",
        context,
    )


def render_import_form(
    request: Request,
    *,
    title: str,
    description: str,
    columns: list[str],
    sample_path: str,
    back_url: str,
    note: str = "",
    success_message: str = "",
    error_message: str = "",
    result_url: str = "",
    active_admin_nav: str = "",
):
    context = {
        "title": title,
        "description": description,
        "columns": columns,
        "sample_path": sample_path,
        "back_url": back_url,
        "note": note,
        "success_message": success_message,
        "error_message": error_message,
        "result_url": result_url,
    }
    if active_admin_nav:
        context.update(get_admin_layout_context(active_admin_nav))

    return templates.TemplateResponse(request, "import_form.html", context)


async def save_upload_to_temp_file(file: UploadFile) -> Path:
    suffix = Path(file.filename or "").suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        return Path(temp_file.name)
