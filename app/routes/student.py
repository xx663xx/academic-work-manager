from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse

from app.routes.shared import get_student_layout_context, role_titles, templates


router = APIRouter(prefix="/student")

DEMO_AVAILABLE_TOPICS = [
    {
        "title": "Разработка веб-приложения для учета учебных работ",
        "work_type": "Курсовая работа",
        "teacher_name": "Иванова Мария Александровна",
        "status": "свободно",
    },
    {
        "title": "Проектирование базы данных для распределения тем",
        "work_type": "ВКР/курсовая",
        "teacher_name": "Петров Алексей Сергеевич",
        "status": "ожидает подтверждения",
    },
    {
        "title": "Автоматизация формирования отчетов по практике",
        "work_type": "ВКР",
        "teacher_name": "Смирнова Елена Викторовна",
        "status": "свободно",
    },
]

DEMO_STUDENT_ASSIGNMENT = {
    "student_name": "Соколов Никита Андреевич",
    "study_group": "ИС-31",
    "course": 3,
    "work_type": "Курсовая работа",
    "topic_title": "Разработка веб-приложения для учета учебных работ",
    "teacher_name": "Иванова Мария Александровна",
    "status": "ожидает подтверждения",
}


@router.get("")
async def student_dashboard(request: Request):
    return RedirectResponse(url="/student/topics", status_code=303)


@router.get("/topics")
async def student_topics(request: Request):
    return render_student_page(
        request,
        active_tab="topics",
        topics=DEMO_AVAILABLE_TOPICS,
    )


@router.get("/assignment")
async def student_assignment(request: Request):
    return render_student_page(
        request,
        active_tab="assignment",
        assignment=DEMO_STUDENT_ASSIGNMENT,
    )


def render_student_page(
    request: Request,
    *,
    active_tab: str,
    topics: list[dict] | None = None,
    assignment: dict | None = None,
):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "student_workspace": {
                "active_tab": active_tab,
                "topics": topics or [],
                "assignment": assignment,
            },
            "roles": role_titles(),
            **get_student_layout_context(active_tab),
        },
    )
