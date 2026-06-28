from app.routes.shared import ROLES, role_titles, templates
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "roles": role_titles(),
            "next_steps": [
                "подключить SQLite",
                "добавить импорт студентов",
                "добавить импорт преподавателей",
                "сделать назначение темы",
            ],
        },
    )


@router.get("/login")
async def login(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "roles": ROLES,
        },
    )
