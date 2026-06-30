from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse

from app.database import (
    clear_all_data,
    create_assignment,
    get_assignment,
    get_assignments,
    get_students,
    get_teachers,
    get_work_types_for_course,
    init_db,
    update_assignment,
)
from app.excel_io import (
    export_assignments_to_excel,
    import_students_from_excel,
    import_teachers_from_excel,
)
from app.routes.shared import (
    get_admin_layout_context,
    render_dashboard,
    render_import_form,
    role_titles,
    save_upload_to_temp_file,
    templates,
)


router = APIRouter(prefix="/admin")

STATUS_LABELS = {
    "free": "свободно",
    "pending": "ожидает подтверждения",
    "confirmed": "подтверждено",
    "rejected": "отказано",
    "changed": "изменено",
}
STATUS_TABLE_LABELS = {
    "free": "свободно",
    "pending": "ожидает",
    "confirmed": "подтверждено",
    "rejected": "отказано",
    "changed": "изменено",
}
STATUS_OPTIONS = [
    ("pending", "ожидает подтверждения"),
    ("confirmed", "подтверждено"),
    ("rejected", "отказано"),
    ("changed", "изменено"),
]


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
            "primary_action_label": "Загрузить Excel",
            "primary_action_url": "/admin/import/students",
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
            "primary_action_label": "Загрузить Excel",
            "primary_action_url": "/admin/import/teachers",
            **get_admin_layout_context("teachers"),
        },
    )


@router.get("/import")
async def admin_import(request: Request):
    return render_admin_import(request)


@router.post("/import/clear")
async def admin_clear_data(
    request: Request,
    confirmation: str = Form(""),
):
    if confirmation.strip() != "ОЧИСТИТЬ":
        return render_admin_import(
            request,
            error_message="Для очистки нужно ввести ОЧИСТИТЬ.",
        )

    clear_all_data()
    return render_admin_import(
        request,
        success_message="База данных полностью очищена. Загрузите студентов и преподавателей заново.",
    )


def render_admin_import(
    request: Request,
    *,
    success_message: str = "",
    error_message: str = "",
):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "admin_import": {
                "options": [
                    {
                        "title": "Студенты",
                        "description": "Загрузить список студентов из Excel-файла.",
                        "url": "/admin/import/students",
                    },
                    {
                        "title": "Преподаватели",
                        "description": "Загрузить список преподавателей из Excel-файла.",
                        "url": "/admin/import/teachers",
                    },
                ],
                "success_message": success_message,
                "error_message": error_message,
            },
            "roles": role_titles(),
            **get_admin_layout_context("import"),
        },
    )


@router.get("/assignments")
async def admin_assignments(request: Request):
    init_db()
    assignments = add_status_labels(get_assignments())
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "admin_assignments": {
                "assignments": assignments,
                "assignments_count": len(assignments),
            },
            "roles": role_titles(),
            **get_admin_layout_context("assignments"),
        },
    )


@router.get("/export/download")
async def admin_export_download(
    request: Request,
    background_tasks: BackgroundTasks,
):
    init_db()
    with NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
        export_path = Path(temp_file.name)

    try:
        export_assignments_to_excel(export_path)
    except ValueError as error:
        remove_file(export_path)
        assignments = add_status_labels(get_assignments())
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "admin_assignments": {
                    "assignments": assignments,
                    "assignments_count": len(assignments),
                    "error_message": str(error),
                },
                "roles": role_titles(),
                **get_admin_layout_context("assignments"),
            },
        )

    background_tasks.add_task(remove_file, export_path)
    return FileResponse(
        export_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="academic_work_assignments.xlsx",
        background=background_tasks,
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


@router.get("/assignments/{assignment_id}/edit")
async def admin_edit_assignment(
    request: Request,
    assignment_id: int,
):
    assignment = get_assignment(assignment_id)
    if assignment is None:
        assignments = add_status_labels(get_assignments())
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "admin_assignments": {
                    "assignments": assignments,
                    "assignments_count": len(assignments),
                    "error_message": "Назначение не найдено.",
                },
                "roles": role_titles(),
                **get_admin_layout_context("assignments"),
            },
        )

    return render_assignment_edit_form(request, assignment=assignment)


@router.post("/assignments/{assignment_id}/edit")
async def admin_update_assignment(
    request: Request,
    assignment_id: int,
    teacher_id: str = Form(""),
    topic_title: str = Form(""),
    work_type: str = Form(""),
    status: str = Form(""),
    comment: str = Form(""),
):
    selected_teacher_id = parse_optional_int(teacher_id)
    current_assignment = get_assignment(assignment_id)
    if current_assignment is None:
        assignments = add_status_labels(get_assignments())
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "admin_assignments": {
                    "assignments": assignments,
                    "assignments_count": len(assignments),
                    "error_message": "Назначение не найдено.",
                },
                "roles": role_titles(),
                **get_admin_layout_context("assignments"),
            },
        )
    if selected_teacher_id is None:
        return render_assignment_edit_form(
            request,
            assignment=current_assignment,
            error_message="Выберите преподавателя.",
            form_values={
                "teacher_id": selected_teacher_id,
                "topic_title": topic_title,
                "work_type": work_type,
                "status": status,
                "comment": comment,
            },
        )

    try:
        assignment = update_assignment(
            assignment_id,
            teacher_id=selected_teacher_id,
            topic_title=topic_title,
            work_type=work_type,
            status=status,
            comment=comment,
            changed_by="admin",
            reason="Администратор изменил назначение",
        )
    except ValueError as error:
        return render_assignment_edit_form(
            request,
            assignment=current_assignment,
            error_message=str(error),
            form_values={
                "teacher_id": selected_teacher_id,
                "topic_title": topic_title,
                "work_type": work_type,
                "status": status,
                "comment": comment,
            },
        )

    return render_assignment_edit_form(
        request,
        assignment=assignment,
        success_message="Назначение обновлено.",
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


def render_assignment_edit_form(
    request: Request,
    *,
    assignment: dict,
    success_message: str = "",
    error_message: str = "",
    form_values: dict | None = None,
):
    init_db()
    values = form_values or {
        "teacher_id": assignment["teacher_id"],
        "topic_title": assignment["topic_title"],
        "work_type": assignment["work_type"],
        "status": assignment["status"],
        "comment": assignment["comment"],
    }
    work_types = get_work_types_for_course(assignment["course"])

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "admin_assignment_edit": {
                "assignment": add_status_labels([assignment])[0],
                "teachers": get_teachers(),
                "work_types": work_types,
                "statuses": STATUS_OPTIONS,
                "success_message": success_message,
                "error_message": error_message,
                "form_values": values,
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


def add_status_labels(rows: list[dict]) -> list[dict]:
    labeled_rows = []
    for row in rows:
        labeled_row = dict(row)
        labeled_row["status_label"] = STATUS_TABLE_LABELS.get(
            labeled_row["status"],
            labeled_row["status"],
        )
        labeled_row["status_title"] = STATUS_LABELS.get(
            labeled_row["status"],
            labeled_row["status"],
        )
        labeled_rows.append(labeled_row)
    return labeled_rows


def remove_file(file_path: Path) -> None:
    file_path.unlink(missing_ok=True)


@router.get("/import/students")
async def admin_import_students(request: Request):
    return render_import_form(
        request,
        title="Импорт студентов",
        description="Загрузка справочника студентов из Excel-файла.",
        columns=["ФИО", "Группа", "Курс", "Логин", "Контакт"],
        sample_path="samples/students.xlsx",
        back_url="/admin/students",
        active_admin_nav="import",
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
            back_url="/admin/students",
            error_message="Выберите файл в формате .xlsx.",
            active_admin_nav="import",
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
            back_url="/admin/students",
            error_message=str(error),
            active_admin_nav="import",
        )
    finally:
        temp_path.unlink(missing_ok=True)

    return render_import_form(
        request,
        title="Импорт студентов",
        description="Загрузка справочника студентов из Excel-файла.",
        columns=["ФИО", "Группа", "Курс", "Логин", "Контакт"],
        sample_path="samples/students.xlsx",
        back_url="/admin/students",
        success_message=f"Загружено студентов: {imported_count}.",
        result_url="/admin/students",
        active_admin_nav="import",
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
        back_url="/admin/teachers",
        active_admin_nav="import",
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
            back_url="/admin/teachers",
            error_message="Выберите файл в формате .xlsx.",
            active_admin_nav="import",
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
            back_url="/admin/teachers",
            error_message=str(error),
            active_admin_nav="import",
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
        back_url="/admin/teachers",
        success_message=f"Загружено преподавателей: {imported_count}.",
        result_url="/admin/teachers",
        active_admin_nav="import",
    )
