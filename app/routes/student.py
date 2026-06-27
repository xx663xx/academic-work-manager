from fastapi import APIRouter, Request

from app.routes.shared import render_dashboard


router = APIRouter(prefix="/student")


@router.get("")
async def student_dashboard(request: Request):
    return render_dashboard(request, "student")
