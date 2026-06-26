from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import get_students, get_teachers, init_db
from app.excel_io import import_students_from_excel, import_teachers_from_excel


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
            {"label": "Назначить тему студенту", "url": "/admin/assignments/new"},
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
):
    return templates.TemplateResponse(
        request,
        "import_form.html",
        {
            "title": title,
            "description": description,
            "columns": columns,
            "sample_path": sample_path,
            "back_url": back_url,
            "note": note,
            "success_message": success_message,
            "error_message": error_message,
            "result_url": result_url,
        },
    )


def get_work_types_for_course(course: int) -> list[str]:
    if course == 3:
        return ["Курсовая работа"]
    if course == 4:
        return ["ВКР", "ВКР/курсовая"]
    return []


async def save_upload_to_temp_file(file: UploadFile) -> Path:
    suffix = Path(file.filename or "").suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        return Path(temp_file.name)


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


@app.get("/admin/assignments/new")
async def admin_new_assignment(
    request: Request,
    student_id: int | None = Query(default=None),
):
    init_db()
    students = get_students()
    teachers = get_teachers()
    selected_student = next(
        (student for student in students if student["id"] == student_id),
        None,
    )
    work_types = (
        get_work_types_for_course(selected_student["course"])
        if selected_student
        else []
    )

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "assignment_form": {
                "students": students,
                "teachers": teachers,
                "selected_student": selected_student,
                "work_types": work_types,
            },
            "roles": [role["title"] for role in ROLES],
        },
    )


@app.get("/admin/import/students")
async def admin_import_students(request: Request):
    return render_import_form(
        request,
        title="Импорт студентов",
        description="Загрузка справочника студентов из Excel-файла.",
        columns=["ФИО", "Группа", "Курс", "Логин", "Контакт"],
        sample_path="samples/students.xlsx",
        back_url="/admin",
    )


@app.post("/admin/import/students")
async def admin_import_students_submit(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".xlsx"):
        return render_import_form(
            request,
            title="Импорт студентов",
            description="Загрузка справочника студентов из Excel-файла.",
            columns=["ФИО", "Группа", "Курс", "Логин", "Контакт"],
            sample_path="samples/students.xlsx",
            back_url="/admin",
            error_message="Выберите файл в формате .xlsx.",
        )

    temp_path = await save_upload_to_temp_file(file)
    try:
        imported_count = import_students_from_excel(temp_path)
    except ValueError as error:
        return render_import_form(
            request,
            title="Импорт студентов",
            description="Загрузка справочника студентов из Excel-файла.",
            columns=["ФИО", "Группа", "Курс", "Логин", "Контакт"],
            sample_path="samples/students.xlsx",
            back_url="/admin",
            error_message=str(error),
        )
    finally:
        temp_path.unlink(missing_ok=True)

    return render_import_form(
        request,
        title="Импорт студентов",
        description="Загрузка справочника студентов из Excel-файла.",
        columns=["ФИО", "Группа", "Курс", "Логин", "Контакт"],
        sample_path="samples/students.xlsx",
        back_url="/admin",
        success_message=f"Загружено студентов: {imported_count}.",
        result_url="/admin/students",
    )


@app.get("/admin/import/teachers")
async def admin_import_teachers(request: Request):
    return render_import_form(
        request,
        title="Импорт преподавателей",
        description="Загрузка справочника преподавателей из Excel-файла.",
        columns=[
            "ФИО",
            "Должность",
            "Ученая степень",
            "Ученое звание",
            "Направление",
            "Контакт",
        ],
        sample_path="samples/teachers.xlsx",
        note="Ученая степень и ученое звание могут быть пустыми. Должность и ФИО обязательны.",
        back_url="/admin",
    )


@app.post("/admin/import/teachers")
async def admin_import_teachers_submit(request: Request, file: UploadFile = File(...)):
    columns = [
        "ФИО",
        "Должность",
        "Ученая степень",
        "Ученое звание",
        "Направление",
        "Контакт",
    ]
    note = "Ученая степень и ученое звание могут быть пустыми. Должность и ФИО обязательны."

    if not file.filename or not file.filename.endswith(".xlsx"):
        return render_import_form(
            request,
            title="Импорт преподавателей",
            description="Загрузка справочника преподавателей из Excel-файла.",
            columns=columns,
            sample_path="samples/teachers.xlsx",
            note=note,
            back_url="/admin",
            error_message="Выберите файл в формате .xlsx.",
        )

    temp_path = await save_upload_to_temp_file(file)
    try:
        imported_count = import_teachers_from_excel(temp_path)
    except ValueError as error:
        return render_import_form(
            request,
            title="Импорт преподавателей",
            description="Загрузка справочника преподавателей из Excel-файла.",
            columns=columns,
            sample_path="samples/teachers.xlsx",
            note=note,
            back_url="/admin",
            error_message=str(error),
        )
    finally:
        temp_path.unlink(missing_ok=True)

    return render_import_form(
        request,
        title="Импорт преподавателей",
        description="Загрузка справочника преподавателей из Excel-файла.",
        columns=columns,
        sample_path="samples/teachers.xlsx",
        note=note,
        back_url="/admin",
        success_message=f"Загружено преподавателей: {imported_count}.",
        result_url="/admin/teachers",
    )


@app.get("/teacher")
async def teacher_dashboard(request: Request):
    return render_dashboard(request, "teacher")


@app.get("/student")
async def student_dashboard(request: Request):
    return render_dashboard(request, "student")
