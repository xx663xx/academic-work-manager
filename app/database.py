import sqlite3
from pathlib import Path


DB_PATH = Path("academic_work_manager.sqlite3")

ASSIGNMENT_STATUSES = {
    "free",
    "pending",
    "confirmed",
    "rejected",
    "changed",
}

WORK_TYPES_BY_COURSE = {
    3: ("Курсовая работа",),
    4: ("ВКР", "ВКР/курсовая"),
}

TOPIC_WORK_TYPES = {
    work_type
    for work_types in WORK_TYPES_BY_COURSE.values()
    for work_type in work_types
}


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


def get_work_types_for_course(course):
    try:
        return list(WORK_TYPES_BY_COURSE[int(course)])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Тип работы определяется только для 3 и 4 курса")


def get_default_work_type_for_course(course):
    return get_work_types_for_course(course)[0]


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


def get_student(student_id, db_path=DB_PATH):
    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, full_name, study_group, course, login, contact
            FROM students
            WHERE id = ?
            """,
            (student_id,),
        ).fetchone()
    return dict(row) if row else None


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


def get_teacher(teacher_id, db_path=DB_PATH):
    with get_connection(db_path) as connection:
        row = connection.execute(
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
            WHERE id = ?
            """,
            (teacher_id,),
        ).fetchone()
    return dict(row) if row else None


def create_topic(
    teacher_id,
    title,
    work_type,
    *,
    description="",
    reserved_student_id=None,
    status="free",
    db_path=DB_PATH,
):
    init_db(db_path)
    title = _normalize_required_text(title, "Название темы не может быть пустым")
    work_type = _normalize_topic_work_type(work_type)
    description = _clean_optional_text(description)
    status = _normalize_assignment_status(status)

    with get_connection(db_path) as connection:
        if _get_teacher_row(connection, teacher_id) is None:
            raise ValueError("Преподаватель не найден")

        if reserved_student_id is not None:
            if _get_student_row(connection, reserved_student_id) is None:
                raise ValueError("Студент для закрепления темы не найден")

        cursor = connection.execute(
            """
            INSERT INTO topics (
                title,
                work_type,
                description,
                teacher_id,
                reserved_student_id,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                work_type,
                description,
                teacher_id,
                reserved_student_id,
                status,
            ),
        )
        topic_id = cursor.lastrowid

    return get_topic(topic_id, db_path)


def get_topic(topic_id, db_path=DB_PATH):
    with get_connection(db_path) as connection:
        row = _get_topic_with_teacher_row(connection, topic_id)
    return dict(row) if row else None


def get_teacher_topics(teacher_id, db_path=DB_PATH):
    init_db(db_path)
    with get_connection(db_path) as connection:
        if _get_teacher_row(connection, teacher_id) is None:
            raise ValueError("Преподаватель не найден")

        rows = connection.execute(
            """
            SELECT
                topics.id,
                topics.title,
                topics.work_type,
                topics.description,
                topics.teacher_id,
                teachers.full_name AS teacher_name,
                topics.reserved_student_id,
                students.full_name AS reserved_student_name,
                topics.status
            FROM topics
            JOIN teachers ON teachers.id = topics.teacher_id
            LEFT JOIN students ON students.id = topics.reserved_student_id
            WHERE topics.teacher_id = ?
            ORDER BY topics.status, topics.title
            """,
            (teacher_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_available_topics_for_student(student_id, db_path=DB_PATH):
    init_db(db_path)
    with get_connection(db_path) as connection:
        student = _get_student_row(connection, student_id)
        if student is None:
            raise ValueError("Студент не найден")

        allowed_work_types = get_work_types_for_course(student["course"])
        placeholders = ", ".join("?" for _ in allowed_work_types)
        rows = connection.execute(
            f"""
            SELECT
                topics.id,
                topics.title,
                topics.work_type,
                topics.description,
                topics.teacher_id,
                teachers.full_name AS teacher_name,
                topics.reserved_student_id,
                students.full_name AS reserved_student_name,
                topics.status
            FROM topics
            JOIN teachers ON teachers.id = topics.teacher_id
            LEFT JOIN students ON students.id = topics.reserved_student_id
            WHERE topics.status = 'free'
              AND topics.work_type IN ({placeholders})
              AND (
                  topics.reserved_student_id IS NULL
                  OR topics.reserved_student_id = ?
              )
            ORDER BY teachers.full_name, topics.title
            """,
            (*allowed_work_types, student_id),
        ).fetchall()
    return [dict(row) for row in rows]


def get_student_assignment(student_id, db_path=DB_PATH):
    init_db(db_path)
    with get_connection(db_path) as connection:
        if _get_student_row(connection, student_id) is None:
            raise ValueError("Студент не найден")

        row = connection.execute(
            """
            SELECT
                assignments.id,
                assignments.student_id,
                students.full_name AS student_name,
                students.study_group,
                students.course,
                assignments.topic_id,
                assignments.topic_title,
                assignments.work_type,
                assignments.teacher_id,
                teachers.full_name AS teacher_name,
                assignments.status,
                assignments.comment,
                assignments.created_at,
                assignments.updated_at
            FROM assignments
            JOIN students ON students.id = assignments.student_id
            JOIN teachers ON teachers.id = assignments.teacher_id
            WHERE assignments.student_id = ?
            """,
            (student_id,),
        ).fetchone()
    return dict(row) if row else None


def choose_topic_for_student(
    student_id,
    topic_id,
    *,
    changed_by="student",
    db_path=DB_PATH,
):
    init_db(db_path)
    changed_by = _normalize_required_text(changed_by, "Не указано, кто выбрал тему")

    with get_connection(db_path) as connection:
        student = _get_student_row(connection, student_id)
        if student is None:
            raise ValueError("Студент не найден")

        topic = _get_topic_row(connection, topic_id)
        if topic is None:
            raise ValueError("Тема не найдена")
        if topic["status"] != "free":
            raise ValueError("Тема уже недоступна для выбора")
        if (
            topic["reserved_student_id"] is not None
            and topic["reserved_student_id"] != student_id
        ):
            raise ValueError("Тема закреплена за другим студентом")

        _normalize_work_type_for_course(topic["work_type"], student["course"])

        existing_assignment = connection.execute(
            "SELECT id FROM assignments WHERE student_id = ?",
            (student_id,),
        ).fetchone()
        if existing_assignment:
            raise ValueError("Для студента уже есть назначение")

        cursor = connection.execute(
            """
            INSERT INTO assignments (
                student_id,
                topic_id,
                teacher_id,
                topic_title,
                work_type,
                status,
                comment
            )
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                student_id,
                topic_id,
                topic["teacher_id"],
                topic["title"],
                topic["work_type"],
                "",
            ),
        )
        assignment_id = cursor.lastrowid
        connection.execute(
            """
            UPDATE topics
            SET status = 'pending', reserved_student_id = ?
            WHERE id = ?
            """,
            (student_id, topic_id),
        )
        _insert_assignment_history(
            connection,
            assignment_id,
            "assignment",
            None,
            f"{topic['title']} / pending",
            changed_by,
            "Студент выбрал тему",
        )

    return get_assignment(assignment_id, db_path)


def get_teacher_topic_requests(teacher_id, *, status="pending", db_path=DB_PATH):
    init_db(db_path)
    with get_connection(db_path) as connection:
        if _get_teacher_row(connection, teacher_id) is None:
            raise ValueError("Преподаватель не найден")

        status_filter = ""
        params = [teacher_id]
        if status is not None:
            status = _normalize_assignment_status(status)
            status_filter = "AND assignments.status = ?"
            params.append(status)

        rows = connection.execute(
            f"""
            SELECT
                assignments.id AS assignment_id,
                assignments.student_id,
                students.full_name AS student_name,
                students.study_group,
                students.course,
                assignments.topic_id,
                assignments.topic_title,
                assignments.work_type,
                assignments.teacher_id,
                teachers.full_name AS teacher_name,
                assignments.status,
                assignments.comment,
                assignments.created_at,
                assignments.updated_at
            FROM assignments
            JOIN students ON students.id = assignments.student_id
            JOIN teachers ON teachers.id = assignments.teacher_id
            WHERE assignments.teacher_id = ?
              AND assignments.topic_id IS NOT NULL
              {status_filter}
            ORDER BY assignments.updated_at DESC, students.full_name
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def confirm_topic_request(
    assignment_id,
    *,
    changed_by="teacher",
    reason="Преподаватель подтвердил тему",
    db_path=DB_PATH,
):
    return _set_topic_request_status(
        assignment_id,
        assignment_status="confirmed",
        topic_status="confirmed",
        changed_by=changed_by,
        reason=reason,
        db_path=db_path,
    )


def reject_topic_request(
    assignment_id,
    *,
    changed_by="teacher",
    reason="Преподаватель отклонил тему",
    db_path=DB_PATH,
):
    return _set_topic_request_status(
        assignment_id,
        assignment_status="rejected",
        topic_status="free",
        clear_topic_reservation=True,
        changed_by=changed_by,
        reason=reason,
        db_path=db_path,
    )


def get_assignments(db_path=DB_PATH):
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                assignments.id,
                assignments.student_id,
                students.full_name AS student_name,
                students.study_group,
                students.course,
                assignments.topic_id,
                assignments.topic_title,
                assignments.work_type,
                assignments.teacher_id,
                teachers.full_name AS teacher_name,
                assignments.status,
                assignments.comment,
                assignments.created_at,
                assignments.updated_at
            FROM assignments
            JOIN students ON students.id = assignments.student_id
            JOIN teachers ON teachers.id = assignments.teacher_id
            ORDER BY students.study_group, students.full_name
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_assignment(assignment_id, db_path=DB_PATH):
    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT
                assignments.id,
                assignments.student_id,
                students.full_name AS student_name,
                students.study_group,
                students.course,
                assignments.topic_id,
                assignments.topic_title,
                assignments.work_type,
                assignments.teacher_id,
                teachers.full_name AS teacher_name,
                assignments.status,
                assignments.comment,
                assignments.created_at,
                assignments.updated_at
            FROM assignments
            JOIN students ON students.id = assignments.student_id
            JOIN teachers ON teachers.id = assignments.teacher_id
            WHERE assignments.id = ?
            """,
            (assignment_id,),
        ).fetchone()
    return dict(row) if row else None


def create_assignment(
    student_id,
    teacher_id,
    topic_title,
    *,
    work_type=None,
    status="pending",
    comment="",
    topic_id=None,
    changed_by="admin",
    reason="Первичное назначение темы",
    db_path=DB_PATH,
):
    init_db(db_path)
    topic_title = _normalize_required_text(topic_title, "Тема не может быть пустой")
    status = _normalize_assignment_status(status)
    changed_by = _normalize_required_text(changed_by, "Не указано, кто изменил назначение")
    comment = _clean_optional_text(comment)

    with get_connection(db_path) as connection:
        student = _get_student_row(connection, student_id)
        if student is None:
            raise ValueError("Студент не найден")

        if _get_teacher_row(connection, teacher_id) is None:
            raise ValueError("Преподаватель не найден")

        existing_assignment = connection.execute(
            "SELECT id FROM assignments WHERE student_id = ?",
            (student_id,),
        ).fetchone()
        if existing_assignment:
            raise ValueError("Для студента уже есть назначение")

        work_type = _normalize_work_type_for_course(work_type, student["course"])
        cursor = connection.execute(
            """
            INSERT INTO assignments (
                student_id,
                topic_id,
                teacher_id,
                topic_title,
                work_type,
                status,
                comment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                topic_id,
                teacher_id,
                topic_title,
                work_type,
                status,
                comment,
            ),
        )
        assignment_id = cursor.lastrowid
        _insert_assignment_history(
            connection,
            assignment_id,
            "assignment",
            None,
            f"{topic_title} / {status}",
            changed_by,
            reason,
        )

    return get_assignment(assignment_id, db_path)


def update_assignment(
    assignment_id,
    *,
    teacher_id=None,
    topic_title=None,
    work_type=None,
    status=None,
    comment=None,
    changed_by="admin",
    reason="Изменение назначения",
    db_path=DB_PATH,
):
    init_db(db_path)
    changed_by = _normalize_required_text(changed_by, "Не указано, кто изменил назначение")

    with get_connection(db_path) as connection:
        current = connection.execute(
            """
            SELECT assignments.id, assignments.teacher_id, assignments.topic_title,
                   assignments.work_type, assignments.status, assignments.comment,
                   students.course
            FROM assignments
            JOIN students ON students.id = assignments.student_id
            WHERE assignments.id = ?
            """,
            (assignment_id,),
        ).fetchone()
        if current is None:
            raise ValueError("Назначение не найдено")

        updates = {}
        if teacher_id is not None:
            if _get_teacher_row(connection, teacher_id) is None:
                raise ValueError("Преподаватель не найден")
            updates["teacher_id"] = teacher_id
        if topic_title is not None:
            updates["topic_title"] = _normalize_required_text(
                topic_title,
                "Тема не может быть пустой",
            )
        if work_type is not None:
            updates["work_type"] = _normalize_work_type_for_course(
                work_type,
                current["course"],
            )
        if status is not None:
            updates["status"] = _normalize_assignment_status(status)
        if comment is not None:
            updates["comment"] = _clean_optional_text(comment)

        changed_fields = {
            field: value
            for field, value in updates.items()
            if str(current[field] or "") != str(value or "")
        }
        if not changed_fields:
            return get_assignment(assignment_id, db_path)

        set_clause = ", ".join(f"{field} = ?" for field in changed_fields)
        values = list(changed_fields.values())
        values.append(assignment_id)
        connection.execute(
            f"""
            UPDATE assignments
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )

        for field, new_value in changed_fields.items():
            _insert_assignment_history(
                connection,
                assignment_id,
                field,
                current[field],
                new_value,
                changed_by,
                reason,
            )

    return get_assignment(assignment_id, db_path)


def get_assignment_history(assignment_id, db_path=DB_PATH):
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                assignment_id,
                field_name,
                old_value,
                new_value,
                changed_by,
                changed_at,
                reason
            FROM assignment_history
            WHERE assignment_id = ?
            ORDER BY changed_at, id
            """,
            (assignment_id,),
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


def _get_student_row(connection, student_id):
    return connection.execute(
        """
        SELECT id, full_name, study_group, course, login, contact
        FROM students
        WHERE id = ?
        """,
        (student_id,),
    ).fetchone()


def _get_teacher_row(connection, teacher_id):
    return connection.execute(
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
        WHERE id = ?
        """,
        (teacher_id,),
    ).fetchone()


def _get_topic_row(connection, topic_id):
    return connection.execute(
        """
        SELECT
            id,
            title,
            work_type,
            description,
            teacher_id,
            reserved_student_id,
            status
        FROM topics
        WHERE id = ?
        """,
        (topic_id,),
    ).fetchone()


def _get_topic_with_teacher_row(connection, topic_id):
    return connection.execute(
        """
        SELECT
            topics.id,
            topics.title,
            topics.work_type,
            topics.description,
            topics.teacher_id,
            teachers.full_name AS teacher_name,
            topics.reserved_student_id,
            students.full_name AS reserved_student_name,
            topics.status
        FROM topics
        JOIN teachers ON teachers.id = topics.teacher_id
        LEFT JOIN students ON students.id = topics.reserved_student_id
        WHERE topics.id = ?
        """,
        (topic_id,),
    ).fetchone()


def _set_topic_request_status(
    assignment_id,
    *,
    assignment_status,
    topic_status,
    clear_topic_reservation=False,
    changed_by,
    reason,
    db_path,
):
    init_db(db_path)
    assignment_status = _normalize_assignment_status(assignment_status)
    topic_status = _normalize_assignment_status(topic_status)
    changed_by = _normalize_required_text(changed_by, "Не указано, кто изменил заявку")

    with get_connection(db_path) as connection:
        current = connection.execute(
            """
            SELECT
                id,
                topic_id,
                status
            FROM assignments
            WHERE id = ?
            """,
            (assignment_id,),
        ).fetchone()
        if current is None:
            raise ValueError("Заявка не найдена")
        if current["topic_id"] is None:
            raise ValueError("Назначение не связано с темой преподавателя")
        if current["status"] != "pending":
            raise ValueError("Заявка уже обработана")

        topic = _get_topic_row(connection, current["topic_id"])
        if topic is None:
            raise ValueError("Тема заявки не найдена")

        connection.execute(
            """
            UPDATE assignments
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (assignment_status, assignment_id),
        )

        if clear_topic_reservation:
            connection.execute(
                """
                UPDATE topics
                SET status = ?, reserved_student_id = NULL
                WHERE id = ?
                """,
                (topic_status, current["topic_id"]),
            )
        else:
            connection.execute(
                """
                UPDATE topics
                SET status = ?
                WHERE id = ?
                """,
                (topic_status, current["topic_id"]),
            )

        _insert_assignment_history(
            connection,
            assignment_id,
            "status",
            current["status"],
            assignment_status,
            changed_by,
            reason,
        )

    return get_assignment(assignment_id, db_path)


def _insert_assignment_history(
    connection,
    assignment_id,
    field_name,
    old_value,
    new_value,
    changed_by,
    reason,
):
    connection.execute(
        """
        INSERT INTO assignment_history (
            assignment_id,
            field_name,
            old_value,
            new_value,
            changed_by,
            reason
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            assignment_id,
            field_name,
            _clean_optional_text(old_value),
            _clean_optional_text(new_value),
            changed_by,
            _clean_optional_text(reason),
        ),
    )


def _normalize_required_text(value, error_message):
    text = _clean_optional_text(value)
    if not text:
        raise ValueError(error_message)
    return text


def _clean_optional_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_assignment_status(status):
    status = _normalize_required_text(status, "Статус назначения не может быть пустым")
    if status not in ASSIGNMENT_STATUSES:
        allowed_statuses = ", ".join(sorted(ASSIGNMENT_STATUSES))
        raise ValueError(f"Недопустимый статус назначения. Допустимо: {allowed_statuses}")
    return status


def _normalize_topic_work_type(work_type):
    work_type = _normalize_required_text(work_type, "Тип работы не может быть пустым")
    if work_type not in TOPIC_WORK_TYPES:
        allowed = ", ".join(sorted(TOPIC_WORK_TYPES))
        raise ValueError(f"Недопустимый тип работы для темы. Допустимо: {allowed}")
    return work_type


def _normalize_work_type_for_course(work_type, course):
    allowed_work_types = get_work_types_for_course(course)
    if work_type is None:
        return allowed_work_types[0]

    work_type = _normalize_required_text(work_type, "Тип работы не может быть пустым")
    if work_type not in allowed_work_types:
        allowed = ", ".join(allowed_work_types)
        raise ValueError(f"Недопустимый тип работы для курса. Допустимо: {allowed}")
    return work_type
