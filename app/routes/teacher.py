from fastapi import APIRouter, Form, Request

from app.routes.shared import (
    get_teacher_layout_context,
    render_dashboard,
    role_titles,
    templates,
)


router = APIRouter(prefix="/teacher")

TOPIC_WORK_TYPES = ["Курсовая работа", "ВКР", "ВКР/курсовая"]


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
    if not title.strip():
        return render_teacher_topics(
            request,
            error_message="Введите название темы.",
            form_values={
                "title": title,
                "work_type": work_type,
                "description": description,
            },
        )
    if work_type not in TOPIC_WORK_TYPES:
        return render_teacher_topics(
            request,
            error_message="Выберите тип работы.",
            form_values={
                "title": title,
                "work_type": work_type,
                "description": description,
            },
        )

    return render_teacher_topics(
        request,
        success_message="Тема добавлена в список.",
        topics=[
            {
                "title": title.strip(),
                "work_type": work_type,
                "description": description.strip(),
            }
        ],
    )


def render_teacher_topics(
    request: Request,
    *,
    success_message: str = "",
    error_message: str = "",
    form_values: dict | None = None,
    topics: list[dict] | None = None,
):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "teacher_topics": {
                "topics": topics or [],
                "work_types": TOPIC_WORK_TYPES,
                "success_message": success_message,
                "error_message": error_message,
                "values": form_values or {},
            },
            "roles": role_titles(),
            **get_teacher_layout_context("topics"),
        },
    )
