from fastapi import APIRouter, Form, Query, Request
from starlette.responses import RedirectResponse

from app.database import (
    choose_topic_for_student,
    get_available_topics_for_student,
    get_student_assignment,
    get_students,
)
from app.routes.shared import get_student_layout_context, role_titles, templates


router = APIRouter(prefix="/student")

STATUS_LABELS = {
    "free": "свободно",
    "pending": "ожидает подтверждения",
    "confirmed": "подтверждено",
    "rejected": "отказано",
    "changed": "изменено",
}


@router.get("")
async def student_dashboard(request: Request):
    return RedirectResponse(url="/student/topics", status_code=303)


@router.get("/topics")
async def student_topics(
    request: Request,
    student_id: int | None = Query(default=None),
):
    return render_student_page(
        request,
        active_tab="topics",
        selected_student_id=student_id,
    )


@router.post("/topics")
async def student_choose_topic(
    request: Request,
    student_id: int = Form(...),
    topic_id: int = Form(...),
):
    try:
        choose_topic_for_student(student_id, topic_id, changed_by="student")
    except ValueError as error:
        return render_student_page(
            request,
            active_tab="topics",
            selected_student_id=student_id,
            error_message=str(error),
        )

    return RedirectResponse(
        url=f"/student/assignment?student_id={student_id}&success=topic_selected",
        status_code=303,
    )


@router.get("/assignment")
async def student_assignment(
    request: Request,
    student_id: int | None = Query(default=None),
):
    return render_student_page(
        request,
        active_tab="assignment",
        selected_student_id=student_id,
    )


def render_student_page(
    request: Request,
    *,
    active_tab: str,
    selected_student_id: int | None = None,
    success_message: str = "",
    error_message: str = "",
):
    success_code = request.query_params.get("success")
    if success_code == "topic_selected":
        success_message = "Тема выбрана и отправлена на подтверждение."

    students = get_students()
    selected_student = get_selected_student(students, selected_student_id)
    topics = []
    assignment = None

    if not students:
        error_message = error_message or "Сначала загрузите список студентов."
    elif selected_student is None:
        error_message = error_message or "Выберите студента."
    else:
        try:
            assignment = add_status_label(get_student_assignment(selected_student["id"]))
            if active_tab == "topics" and assignment is None:
                topics = add_status_labels(
                    get_available_topics_for_student(selected_student["id"])
                )
        except ValueError as error:
            error_message = error_message or str(error)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "student_workspace": {
                "active_tab": active_tab,
                "students": students,
                "selected_student": selected_student,
                "topics": topics,
                "assignment": assignment,
                "success_message": success_message,
                "error_message": error_message,
            },
            "roles": role_titles(),
            **get_student_layout_context(active_tab),
        },
    )


def get_selected_student(students: list[dict], selected_student_id: int | None):
    if not students:
        return None
    if selected_student_id is None:
        return students[0]
    return next(
        (student for student in students if student["id"] == selected_student_id),
        None,
    )


def add_status_label(row: dict | None):
    if row is None:
        return None
    labeled_row = dict(row)
    labeled_row["status_label"] = STATUS_LABELS.get(
        labeled_row["status"],
        labeled_row["status"],
    )
    return labeled_row


def add_status_labels(rows: list[dict]) -> list[dict]:
    return [add_status_label(row) for row in rows]
