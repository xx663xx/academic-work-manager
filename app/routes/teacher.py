from fastapi import APIRouter, Request

from app.routes.shared import render_dashboard


router = APIRouter(prefix="/teacher")


@router.get("")
async def teacher_dashboard(request: Request):
    return render_dashboard(request, "teacher")
