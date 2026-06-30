from fastapi import APIRouter, Form, Query, Request
from starlette.responses import RedirectResponse

from app.database import (
    confirm_topic_request,
    create_topic,
    delete_topic,
    get_topic,
    get_teacher_topic_requests,
    get_teacher_topics,
    get_teachers,
    reject_topic_request,
    update_topic,
)
from app.routes.shared import (
    get_teacher_layout_context,
    render_dashboard,
    role_titles,
    templates,
)


router = APIRouter(prefix="/teacher")

TOPIC_WORK_TYPES = ["Курсовая работа", "ВКР", "ВКР/курсовая"]
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


@router.get("")
async def teacher_dashboard(request: Request):
    return render_dashboard(request, "teacher")


@router.get("/topics")
async def teacher_topics(
    request: Request,
    teacher_id: int | None = Query(default=None),
):
    return render_teacher_topics(request, selected_teacher_id=teacher_id)


@router.post("/topics")
async def teacher_create_topic(
    request: Request,
    teacher_id: str = Form(""),
    title: str = Form(""),
    work_type: str = Form(""),
    description: str = Form(""),
):
    selected_teacher_id = parse_optional_int(teacher_id)
    current_teacher = get_current_teacher(selected_teacher_id)
    if current_teacher is None:
        return render_teacher_topics(
            request,
            selected_teacher_id=selected_teacher_id,
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
            selected_teacher_id=current_teacher["id"],
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
        selected_teacher_id=current_teacher["id"],
    )


@router.get("/requests")
async def teacher_requests(
    request: Request,
    teacher_id: int | None = Query(default=None),
):
    return render_teacher_requests(request, selected_teacher_id=teacher_id)


@router.post("/requests/{assignment_id}/confirm")
async def teacher_confirm_request(
    assignment_id: int,
    teacher_id: int | None = Query(default=None),
):
    confirm_topic_request(assignment_id, changed_by="teacher")
    return RedirectResponse(
        url=build_teacher_redirect_url(
            "/teacher/requests",
            teacher_id,
            success="confirmed",
        ),
        status_code=303,
    )


@router.post("/requests/{assignment_id}/reject")
async def teacher_reject_request(
    assignment_id: int,
    teacher_id: int | None = Query(default=None),
):
    reject_topic_request(assignment_id, changed_by="teacher")
    return RedirectResponse(
        url=build_teacher_redirect_url(
            "/teacher/requests",
            teacher_id,
            success="rejected",
        ),
        status_code=303,
    )


def render_teacher_topics(
    request: Request,
    *,
    selected_teacher_id: int | None = None,
    success_message: str = "",
    error_message: str = "",
    form_values: dict | None = None,
):
    success_code = request.query_params.get("success")
    if success_code == "topic_updated":
        success_message = "Тема обновлена."
    if success_code == "topic_deleted":
        success_message = "Тема удалена."

    teachers = get_teachers()
    current_teacher = get_current_teacher(selected_teacher_id, teachers)
    topics = []
    if not teachers:
        error_message = error_message or "Сначала загрузите список преподавателей."
    elif current_teacher is None:
        error_message = error_message or "Выберите преподавателя."
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
                "teachers": teachers,
                "current_teacher": current_teacher,
                "success_message": success_message,
                "error_message": error_message,
                "form_values": form_values or {},
            },
            "roles": role_titles(),
            **get_teacher_layout_context(
                "topics",
                current_teacher["id"] if current_teacher else None,
            ),
        },
    )


@router.get("/topics/{topic_id}/edit")
async def teacher_edit_topic(
    request: Request,
    topic_id: int,
    teacher_id: int | None = Query(default=None),
):
    current_teacher = get_current_teacher(teacher_id)
    if current_teacher is None:
        return render_teacher_topics(
            request,
            selected_teacher_id=teacher_id,
            error_message="Сначала выберите преподавателя.",
        )

    topic = get_topic(topic_id)
    if topic is None:
        return render_teacher_topics(
            request,
            selected_teacher_id=current_teacher["id"],
            error_message="Тема не найдена.",
        )
    if topic["teacher_id"] != current_teacher["id"]:
        return render_teacher_topics(
            request,
            selected_teacher_id=current_teacher["id"],
            error_message="Можно редактировать только свои темы.",
        )

    return render_teacher_topic_edit(
        request,
        current_teacher=current_teacher,
        topic=topic,
    )


@router.post("/topics/{topic_id}/edit")
async def teacher_update_topic(
    request: Request,
    topic_id: int,
    teacher_id: str = Form(""),
    title: str = Form(""),
    work_type: str = Form(""),
    description: str = Form(""),
):
    selected_teacher_id = parse_optional_int(teacher_id)
    current_teacher = get_current_teacher(selected_teacher_id)
    topic = get_topic(topic_id)
    if current_teacher is None:
        return render_teacher_topics(
            request,
            selected_teacher_id=selected_teacher_id,
            error_message="Сначала выберите преподавателя.",
        )
    if topic is None:
        return render_teacher_topics(
            request,
            selected_teacher_id=current_teacher["id"],
            error_message="Тема не найдена.",
        )
    if topic["teacher_id"] != current_teacher["id"]:
        return render_teacher_topics(
            request,
            selected_teacher_id=current_teacher["id"],
            error_message="Можно редактировать только свои темы.",
        )

    try:
        update_topic(
            topic_id,
            teacher_id=current_teacher["id"],
            title=title,
            work_type=work_type,
            description=description,
        )
    except ValueError as error:
        return render_teacher_topic_edit(
            request,
            current_teacher=current_teacher,
            topic=topic,
            error_message=str(error),
            form_values={
                "title": title,
                "work_type": work_type,
                "description": description,
            },
        )

    return RedirectResponse(
        url=build_teacher_redirect_url(
            "/teacher/topics",
            current_teacher["id"],
            success="topic_updated",
        ),
        status_code=303,
    )


@router.post("/topics/{topic_id}/delete")
async def teacher_delete_topic(
    request: Request,
    topic_id: int,
    teacher_id: str = Form(""),
):
    selected_teacher_id = parse_optional_int(teacher_id)
    current_teacher = get_current_teacher(selected_teacher_id)
    topic = get_topic(topic_id)
    if current_teacher is None:
        return render_teacher_topics(
            request,
            selected_teacher_id=selected_teacher_id,
            error_message="Сначала выберите преподавателя.",
        )
    if topic is None:
        return render_teacher_topics(
            request,
            selected_teacher_id=current_teacher["id"],
            error_message="Тема не найдена.",
        )

    try:
        delete_topic(topic_id, teacher_id=current_teacher["id"])
    except ValueError as error:
        return render_teacher_topic_edit(
            request,
            current_teacher=current_teacher,
            topic=topic,
            error_message=str(error),
        )

    return RedirectResponse(
        url=build_teacher_redirect_url(
            "/teacher/topics",
            current_teacher["id"],
            success="topic_deleted",
        ),
        status_code=303,
    )


def render_teacher_topic_edit(
    request: Request,
    *,
    current_teacher: dict,
    topic: dict,
    success_message: str = "",
    error_message: str = "",
    form_values: dict | None = None,
):
    values = form_values or {
        "title": topic["title"],
        "work_type": topic["work_type"],
        "description": topic["description"],
    }

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "teacher_topic_edit": {
                "topic": add_status_labels([topic])[0],
                "current_teacher": current_teacher,
                "work_types": TOPIC_WORK_TYPES,
                "success_message": success_message,
                "error_message": error_message,
                "form_values": values,
                "can_delete": topic["status"] == "free",
            },
            "roles": role_titles(),
            **get_teacher_layout_context("topics", current_teacher["id"]),
        },
    )


def render_teacher_requests(
    request: Request,
    *,
    selected_teacher_id: int | None = None,
    success_message: str = "",
    error_message: str = "",
):
    success_code = request.query_params.get("success")
    if success_code == "confirmed":
        success_message = "Заявка подтверждена."
    if success_code == "rejected":
        success_message = "Заявка отклонена."

    teachers = get_teachers()
    current_teacher = get_current_teacher(selected_teacher_id, teachers)
    requests = []
    if not teachers:
        error_message = error_message or "Сначала загрузите список преподавателей."
    elif current_teacher is None:
        error_message = error_message or "Выберите преподавателя."
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
                "teachers": teachers,
                "current_teacher": current_teacher,
                "success_message": success_message,
                "error_message": error_message,
            },
            "roles": role_titles(),
            **get_teacher_layout_context(
                "requests",
                current_teacher["id"] if current_teacher else None,
            ),
        },
    )


def get_current_teacher(
    selected_teacher_id: int | None = None,
    teachers: list[dict] | None = None,
):
    if teachers is None:
        teachers = get_teachers()
    if not teachers:
        return None
    if selected_teacher_id is None:
        return teachers[0]
    return next(
        (teacher for teacher in teachers if teacher["id"] == selected_teacher_id),
        None,
    )


def parse_optional_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_teacher_redirect_url(
    base_url: str,
    teacher_id: int | None,
    *,
    success: str,
) -> str:
    params = []
    if teacher_id is not None:
        params.append(f"teacher_id={teacher_id}")
    params.append(f"success={success}")
    return f"{base_url}?{'&'.join(params)}"


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
