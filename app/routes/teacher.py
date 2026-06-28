from fastapi import APIRouter, Form, Request
from starlette.responses import RedirectResponse

from app.database import (
    confirm_topic_request,
    create_topic,
    get_teacher_topic_requests,
    get_teacher_topics,
    get_teachers,
    reject_topic_request,
)
from app.routes.shared import (
    get_teacher_layout_context,
    render_dashboard,
    role_titles,
    templates,
)

from app.routes.shared import render_dashboard
from fastapi import APIRouter, Request

router = APIRouter(prefix="/teacher")

TOPIC_WORK_TYPES = ["Курсовая работа", "ВКР", "ВКР/курсовая"]
STATUS_LABELS = {
    "free": "свободно",
    "pending": "ожидает подтверждения",
    "confirmed": "подтверждено",
    "rejected": "отказано",
    "changed": "изменено",
}


@router.get("")
async def teacher_dashboard(request: Request):
    return render_dashboard(request, "teacher")


@router.get("/topics")
async def teacher_topics(request: Request):
    return render_teacher_topics(request)


@router.post("/topics")
async def teacher_create_topic(
    request: Request,
    title: str = Form(""),
    work_type: str = Form(""),
    description: str = Form(""),
):
    current_teacher = get_current_teacher()
    if current_teacher is None:
        return render_teacher_topics(
            request,
            error_message="Сначала загрузите список преподавателей.",
            form_values={
                "title": title,
                "work_type": work_type,
                "description": description,
            },
        )

    try:
        create_topic(
            current_teacher["id"],
            title,
            work_type,
            description=description,
        )
    except ValueError as error:
        return render_teacher_topics(
            request,
            error_message=str(error),
            form_values={
                "title": title,
                "work_type": work_type,
                "description": description,
            },
        )

    return render_teacher_topics(
        success_message="Тема добавлена в список.",
        request=request,
    )


@router.get("/requests")
async def teacher_requests(request: Request):
    return render_teacher_requests(request)


@router.post("/requests/{assignment_id}/confirm")
async def teacher_confirm_request(assignment_id: int):
    confirm_topic_request(assignment_id, changed_by="teacher")
    return RedirectResponse(url="/teacher/requests?success=confirmed", status_code=303)


@router.post("/requests/{assignment_id}/reject")
async def teacher_reject_request(assignment_id: int):
    reject_topic_request(assignment_id, changed_by="teacher")
    return RedirectResponse(url="/teacher/requests?success=rejected", status_code=303)


def render_teacher_topics(
    request: Request,
    *,
    success_message: str = "",
    error_message: str = "",
    form_values: dict | None = None,
):
    current_teacher = get_current_teacher()
    topics = []
    if current_teacher is None:
        error_message = error_message or "Сначала загрузите список преподавателей."
    else:
        try:
            topics = add_status_labels(get_teacher_topics(current_teacher["id"]))
        except ValueError as error:
            error_message = error_message or str(error)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "teacher_topics": {
                "topics": topics or [],
                "work_types": TOPIC_WORK_TYPES,
                "current_teacher": current_teacher,
                "success_message": success_message,
                "error_message": error_message,
                "values": form_values or {},
            },
            "roles": role_titles(),
            **get_teacher_layout_context("topics"),
        },
    )


def render_teacher_requests(
    request: Request,
    *,
    success_message: str = "",
    error_message: str = "",
):
    success_code = request.query_params.get("success")
    if success_code == "confirmed":
        success_message = "Заявка подтверждена."
    if success_code == "rejected":
        success_message = "Заявка отклонена."

    current_teacher = get_current_teacher()
    requests = []
    if current_teacher is None:
        error_message = error_message or "Сначала загрузите список преподавателей."
    else:
        try:
            requests = add_status_labels(
                get_teacher_topic_requests(current_teacher["id"], status=None)
            )
        except ValueError as error:
            error_message = error_message or str(error)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "teacher_requests": {
                "requests": requests,
                "current_teacher": current_teacher,
                "success_message": success_message,
                "error_message": error_message,
            },
            "roles": role_titles(),
            **get_teacher_layout_context("requests"),
        },
    )


def get_current_teacher():
    teachers = get_teachers()
    return teachers[0] if teachers else None


def add_status_labels(rows: list[dict]) -> list[dict]:
    labeled_rows = []
    for row in rows:
        labeled_row = dict(row)
        labeled_row["status_label"] = STATUS_LABELS.get(
            labeled_row["status"],
            labeled_row["status"],
        )
        labeled_rows.append(labeled_row)
    return labeled_rows