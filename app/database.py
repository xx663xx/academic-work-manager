import sqlite3
from pathlib import Path


DB_PATH = Path("academic_work_manager.sqlite3")


def get_connection(db_path=DB_PATH):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path=DB_PATH):
    with get_connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                study_group TEXT NOT NULL,
                course INTEGER NOT NULL CHECK (course IN (3, 4)),
                login TEXT,
                contact TEXT,
                UNIQUE(full_name, study_group)
            );

            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL UNIQUE,
                position TEXT NOT NULL,
                academic_degree TEXT,
                academic_title TEXT,
                specialization TEXT,
                contact TEXT
            );

            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                work_type TEXT NOT NULL,
                description TEXT,
                teacher_id INTEGER NOT NULL,
                reserved_student_id INTEGER,
                status TEXT NOT NULL DEFAULT 'free',
                FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                FOREIGN KEY (reserved_student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL UNIQUE,
                topic_id INTEGER,
                teacher_id INTEGER NOT NULL,
                topic_title TEXT NOT NULL,
                work_type TEXT NOT NULL,
                status TEXT NOT NULL,
                comment TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (topic_id) REFERENCES topics(id),
                FOREIGN KEY (teacher_id) REFERENCES teachers(id)
            );

            CREATE TABLE IF NOT EXISTS assignment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT NOT NULL,
                changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reason TEXT,
                FOREIGN KEY (assignment_id) REFERENCES assignments(id)
            );
            """
        )


def get_students(db_path=DB_PATH):
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, full_name, study_group, course, login, contact
            FROM students
            ORDER BY study_group, full_name
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_teachers(db_path=DB_PATH):
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                full_name,
                position,
                academic_degree,
                academic_title,
                specialization,
                contact
            FROM teachers
            ORDER BY full_name
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_assignments_for_export(db_path=DB_PATH):
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                students.full_name AS student_name,
                students.study_group,
                students.course,
                assignments.work_type,
                assignments.topic_title,
                teachers.full_name AS teacher_name,
                assignments.status,
                assignments.updated_at
            FROM assignments
            JOIN students ON students.id = assignments.student_id
            JOIN teachers ON teachers.id = assignments.teacher_id
            ORDER BY students.study_group, students.full_name
            """
        ).fetchall()
    return [dict(row) for row in rows]