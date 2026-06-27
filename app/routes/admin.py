from fastapi import APIRouter, File, Query, Request, UploadFile

from app.database import get_students, get_teachers, get_work_types_for_course, init_db
from app.excel_io import import_students_from_excel, import_teachers_from_excel
from app.routes.shared import (
    get_admin_layout_context,
    render_dashboard,
    render_import_form,
    role_titles,
    save_upload_to_temp_file,
    templates,
)


router = APIRouter(prefix="/admin")


@router.get("")
async def admin_dashboard(request: Request):
    return render_dashboard(request, "admin")


@router.get("/students")
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
            **get_admin_layout_context("students"),
        },
    )


@router.get("/teachers")
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
            **get_admin_layout_context("teachers"),
        },
    )


@router.get("/assignments/new")
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
            "roles": role_titles(),
            **get_admin_layout_context("assignments"),
        },
    )


@router.get("/import/students")
async def admin_import_students(request: Request):
    return render_import_form(
        request,
        title="Импорт студентов",
        description="Загрузка справочника студентов из Excel-файла.",
        columns=["ФИО", "Группа", "Курс", "Логин", "Контакт"],
        sample_path="samples/students.xlsx",
        back_url="/admin",
        active_admin_nav="students",
    )


@router.post("/import/students")
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
            active_admin_nav="students",
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
            active_admin_nav="students",
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
        active_admin_nav="students",
    )


@router.get("/import/teachers")
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
        active_admin_nav="teachers",
    )


@router.post("/import/teachers")
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
            active_admin_nav="teachers",
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
            active_admin_nav="teachers",
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
        active_admin_nav="teachers",
    )
