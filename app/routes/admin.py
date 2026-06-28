import tempfile

from app.database import (
    create_assignment,
    get_students,
    get_teachers,
    get_work_types_for_course,
    init_db,
)
from app.database import get_assignments_for_export
from app.database import get_assignments_for_export
from app.excel_io import export_assignments_to_excel
from app.excel_io import export_assignments_to_excel
from app.excel_io import import_students_from_excel, import_teachers_from_excel
from app.routes.shared import (
    get_admin_layout_context,
    render_dashboard,
    render_import_form,
    role_titles,
    save_upload_to_temp_file,
    templates,
)
from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

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
    return render_assignment_form(
        request,
        selected_student_id=student_id,
    )


@router.post("/assignments/new")
async def admin_create_assignment(
    request: Request,
    student_id: str = Form(""),
    teacher_id: str = Form(""),
    topic_title: str = Form(""),
    work_type: str = Form(""),
):
    selected_student_id = parse_optional_int(student_id)
    selected_teacher_id = parse_optional_int(teacher_id)
    if selected_student_id is None:
        return render_assignment_form(
            request,
            error_message="Выберите студента.",
            form_values={
                "teacher_id": selected_teacher_id,
                "topic_title": topic_title,
                "work_type": work_type,
            },
        )
    if selected_teacher_id is None:
        return render_assignment_form(
            request,
            selected_student_id=selected_student_id,
            error_message="Выберите преподавателя.",
            form_values={
                "teacher_id": selected_teacher_id,
                "topic_title": topic_title,
                "work_type": work_type,
            },
        )

    try:
        assignment = create_assignment(
            selected_student_id,
            selected_teacher_id,
            topic_title,
            work_type=work_type or None,
            changed_by="admin",
        )
    except ValueError as error:
        return render_assignment_form(
            request,
            selected_student_id=selected_student_id,
            error_message=str(error),
            form_values={
                "teacher_id": selected_teacher_id,
                "topic_title": topic_title,
                "work_type": work_type,
            },
        )

    return render_assignment_form(
        request,
        selected_student_id=assignment["student_id"],
        success_message="Назначение сохранено.",
        assignment_result=assignment,
        form_values={
            "teacher_id": assignment["teacher_id"],
            "topic_title": assignment["topic_title"],
            "work_type": assignment["work_type"],
        },
    )


def render_assignment_form(
    request: Request,
    *,
    selected_student_id: int | None = None,
    success_message: str = "",
    error_message: str = "",
    assignment_result: dict | None = None,
    form_values: dict | None = None,
):
    init_db()
    students = get_students()
    teachers = get_teachers()
    selected_student = next(
        (student for student in students if student["id"] == selected_student_id),
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
                "success_message": success_message,
                "error_message": error_message,
                "assignment_result": assignment_result,
                "values": form_values or {},
            },
            "roles": role_titles(),
            **get_admin_layout_context("assignments"),
        },
    )


def parse_optional_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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


@router.get("/export")
async def admin_export_page(request: Request):
    try:
        assignments = get_assignments_for_export()
        return templates.TemplateResponse(
            request,
            "export.html",
            {
                "title": "Экспорт назначений",
                "assignments_count": len(assignments),
                "has_assignments": len(assignments) > 0,
                **get_admin_layout_context("export"),
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "export.html",
            {
                "title": "Экспорт назначений",
                "error_message": f"Ошибка при загрузке данных: {str(e)}",
                "assignments_count": 0,
                "has_assignments": False,
                **get_admin_layout_context("export"),
            },
        )


@router.get("/export/download")
async def admin_export_download():
    try:
        assignments = get_assignments_for_export()

        if not assignments:
            return HTMLResponse(
                content="<h1>Ошибка</h1><p>Нет назначений для экспорта.</p><a href='/admin/export'>Вернуться</a>",
                status_code=400
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
            temp_path = tmp_file.name

        export_assignments_to_excel(temp_path)

        return FileResponse(
            path=temp_path,
            filename="assignments.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except ValueError as e:
        return HTMLResponse(
            content=f"<h1>Ошибка</h1><p>{str(e)}</p><a href='/admin/export'>Вернуться</a>",
            status_code=400
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<h1>Ошибка при экспорте</h1><p>{str(e)}</p><a href='/admin/export'>Вернуться</a>",
            status_code=500
        )
