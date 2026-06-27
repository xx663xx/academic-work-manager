from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import admin, home, student, teacher


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Academic Work Manager")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(home.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(student.router)
