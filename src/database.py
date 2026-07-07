"""
SQLite question bank. Stores all parsed questions indexed by topic, difficulty, and paper.
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "question_bank.db"


def get_connection(db_path: str = None) -> sqlite3.Connection:
    path = db_path or str(DB_PATH)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = None):
    conn = get_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            paper_id        TEXT PRIMARY KEY,
            year            INTEGER,
            session         TEXT,
            unit            TEXT,
            syllabus        TEXT,
            paper_file      TEXT,
            ms_file         TEXT,
            parsed_at       TEXT
        );

        CREATE TABLE IF NOT EXISTS questions (
            question_id         TEXT PRIMARY KEY,
            paper_id            TEXT,
            question_number     TEXT,
            topic_head          TEXT,
            topic_signals       TEXT,
            adjunct_count       INTEGER,
            given_values        TEXT,
            given_value_types   TEXT,
            FOREIGN KEY (paper_id) REFERENCES papers(paper_id)
        );

        CREATE TABLE IF NOT EXISTS parts (
            part_id             TEXT PRIMARY KEY,
            question_id         TEXT,
            paper_id            TEXT,
            part_label          TEXT,
            question_text       TEXT,
            marks               INTEGER,
            command_word        TEXT,
            significant_steps   INTEGER,
            mark_breakdown      TEXT,
            worked_steps        TEXT,
            final_answer        TEXT,
            answer_type         TEXT,
            field_distance      INTEGER,
            solvability_score   REAL,
            solvability         TEXT,
            topic_head          TEXT,
            topic_signals       TEXT,
            adjunct_count       INTEGER,
            FOREIGN KEY (question_id) REFERENCES questions(question_id)
        );

        CREATE INDEX IF NOT EXISTS idx_parts_topic    ON parts(topic_head);
        CREATE INDEX IF NOT EXISTS idx_parts_solv     ON parts(solvability_score);
        CREATE INDEX IF NOT EXISTS idx_parts_paper    ON parts(paper_id);
        CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic_head);

        CREATE TABLE IF NOT EXISTS generated_items (
            item_id             TEXT PRIMARY KEY,
            source              TEXT,
            topic               TEXT,
            primary_skill       TEXT,
            secondary_skills    TEXT,
            question_text       TEXT,
            parts               TEXT,
            canonical_solution  TEXT,
            final_answer        TEXT,
            answer_type         TEXT,
            significant_steps   INTEGER,
            marks               INTEGER,
            parameters          TEXT,
            verifier_result     TEXT,
            quality_result      TEXT,
            status              TEXT DEFAULT 'draft',
            created_at          TEXT,
            updated_at          TEXT
        );

        CREATE TABLE IF NOT EXISTS student_attempts (
            attempt_id          TEXT PRIMARY KEY,
            user_id             TEXT,
            item_id             TEXT,
            submitted_answer    TEXT,
            normalized_answer   TEXT,
            is_correct          INTEGER,
            time_seconds        REAL,
            hints_used          INTEGER DEFAULT 0,
            detected_misconceptions TEXT,
            timestamp           TEXT
        );

        CREATE TABLE IF NOT EXISTS skill_mastery (
            user_id             TEXT,
            skill_id            TEXT,
            mastery_probability REAL DEFAULT 0.25,
            last_practiced      TEXT,
            next_due            TEXT,
            correct_streak      INTEGER DEFAULT 0,
            incorrect_streak    INTEGER DEFAULT 0,
            updated_at          TEXT,
            PRIMARY KEY(user_id, skill_id)
        );

        CREATE TABLE IF NOT EXISTS item_stats (
            item_id             TEXT PRIMARY KEY,
            attempts            INTEGER DEFAULT 0,
            correct             INTEGER DEFAULT 0,
            p_correct           REAL,
            avg_time_seconds    REAL,
            hint_rate           REAL,
            empirical_difficulty REAL,
            updated_at          TEXT
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id             TEXT PRIMARY KEY,
            username            TEXT UNIQUE NOT NULL,
            password_hash       TEXT NOT NULL,
            role                TEXT NOT NULL CHECK(role IN ('teacher', 'student')),
            created_at          TEXT
        );

        CREATE TABLE IF NOT EXISTS saved_papers (
            saved_paper_id      TEXT PRIMARY KEY,
            owner_user_id       TEXT NOT NULL,
            name                TEXT NOT NULL,
            questions_json      TEXT NOT NULL,
            created_at          TEXT,
            updated_at          TEXT,
            FOREIGN KEY (owner_user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS classes (
            class_id            TEXT PRIMARY KEY,
            teacher_id          TEXT NOT NULL,
            name                TEXT NOT NULL,
            level               TEXT,
            join_code           TEXT UNIQUE NOT NULL,
            created_at          TEXT,
            FOREIGN KEY (teacher_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            class_id            TEXT NOT NULL,
            student_id          TEXT NOT NULL,
            joined_at           TEXT,
            PRIMARY KEY (class_id, student_id),
            FOREIGN KEY (class_id)   REFERENCES classes(class_id),
            FOREIGN KEY (student_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS assignments (
            assignment_id       TEXT PRIMARY KEY,
            class_id            TEXT NOT NULL,
            title               TEXT NOT NULL,
            questions_json      TEXT NOT NULL,
            due_date            TEXT,
            settings_json       TEXT DEFAULT '{}',
            created_at          TEXT,
            FOREIGN KEY (class_id) REFERENCES classes(class_id)
        );

        CREATE TABLE IF NOT EXISTS submissions (
            submission_id       TEXT PRIMARY KEY,
            assignment_id       TEXT NOT NULL,
            student_id          TEXT NOT NULL,
            status              TEXT DEFAULT 'in_progress'
                                CHECK(status IN ('in_progress','submitted','graded')),
            started_at          TEXT,
            submitted_at        TEXT,
            graded_at           TEXT,
            auto_total          REAL,
            final_total         REAL,
            UNIQUE (assignment_id, student_id),
            FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id),
            FOREIGN KEY (student_id)    REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS submission_answers (
            answer_id           TEXT PRIMARY KEY,
            submission_id       TEXT NOT NULL,
            question_index      INTEGER NOT NULL,
            submitted_answer    TEXT,
            is_correct          INTEGER,
            auto_score          REAL,
            max_score           REAL,
            teacher_score       REAL,
            teacher_comment     TEXT,
            detected_misconceptions TEXT,
            UNIQUE (submission_id, question_index),
            FOREIGN KEY (submission_id) REFERENCES submissions(submission_id)
        );

        CREATE INDEX IF NOT EXISTS idx_gen_items_topic   ON generated_items(topic);
        CREATE INDEX IF NOT EXISTS idx_gen_items_skill   ON generated_items(primary_skill);
        CREATE INDEX IF NOT EXISTS idx_gen_items_status  ON generated_items(status);
        CREATE INDEX IF NOT EXISTS idx_attempts_user     ON student_attempts(user_id);
        CREATE INDEX IF NOT EXISTS idx_attempts_item     ON student_attempts(item_id);
        CREATE INDEX IF NOT EXISTS idx_saved_papers_owner ON saved_papers(owner_user_id);
        CREATE INDEX IF NOT EXISTS idx_classes_teacher    ON classes(teacher_id);
        CREATE INDEX IF NOT EXISTS idx_enroll_student     ON enrollments(student_id);
        CREATE INDEX IF NOT EXISTS idx_assign_class       ON assignments(class_id);
        CREATE INDEX IF NOT EXISTS idx_subs_assignment    ON submissions(assignment_id);
        CREATE INDEX IF NOT EXISTS idx_subs_student       ON submissions(student_id);
        CREATE INDEX IF NOT EXISTS idx_sub_answers_sub    ON submission_answers(submission_id);
    """)
    conn.commit()
    conn.close()


def paper_exists(paper_id: str, db_path: str = None) -> bool:
    conn = get_connection(db_path)
    row = conn.execute("SELECT 1 FROM papers WHERE paper_id = ?", (paper_id,)).fetchone()
    conn.close()
    return row is not None


def insert_paper(paper_id: str, meta: dict, records: list[dict], db_path: str = None):
    conn = get_connection(db_path)
    from datetime import datetime

    conn.execute("""
        INSERT OR REPLACE INTO papers
            (paper_id, year, session, unit, syllabus, paper_file, ms_file, parsed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        paper_id,
        meta.get("year"),
        meta.get("session"),
        meta.get("unit", "P2"),
        meta.get("syllabus", "Edexcel IAL"),
        meta.get("paper_file"),
        meta.get("ms_file"),
        datetime.now().isoformat(),
    ))

    for q in records:
        qnum = q["question_number"]
        question_id = f"{paper_id}_Q{qnum}"

        conn.execute("""
            INSERT OR REPLACE INTO questions
                (question_id, paper_id, question_number, topic_head,
                 topic_signals, adjunct_count, given_values, given_value_types)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            question_id,
            paper_id,
            qnum,
            q.get("topic_head"),
            json.dumps(q.get("topic_signals", [])),
            q.get("adjunct_count", 0),
            json.dumps(q.get("given_values", [])),
            json.dumps(q.get("given_value_types", [])),
        ))

        for part in q.get("parts", []):
            part_label = part.get("part", "?")
            part_id = f"{question_id}_{part_label}"

            conn.execute("""
                INSERT OR REPLACE INTO parts
                    (part_id, question_id, paper_id, part_label, question_text,
                     marks, command_word, significant_steps, mark_breakdown,
                     worked_steps, final_answer, answer_type, field_distance,
                     solvability_score, solvability, topic_head, topic_signals, adjunct_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                part_id,
                question_id,
                paper_id,
                part_label,
                part.get("question_text"),
                part.get("marks"),
                part.get("command_word"),
                part.get("significant_steps"),
                json.dumps(part.get("mark_breakdown", {})),
                json.dumps(part.get("worked_steps", [])),
                part.get("final_answer"),
                part.get("answer_type"),
                part.get("field_distance"),
                part.get("solvability_score"),
                part.get("solvability"),
                q.get("topic_head"),
                json.dumps(q.get("topic_signals", [])),
                q.get("adjunct_count", 0),
            ))

    conn.commit()
    conn.close()


def query_by_topic(topic: str, min_score: float = 0.0, max_score: float = 1.0,
                   limit: int = 10, db_path: str = None) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT * FROM parts
        WHERE topic_head = ?
          AND solvability_score BETWEEN ? AND ?
          AND question_text IS NOT NULL
        ORDER BY solvability_score DESC
        LIMIT ?
    """, (topic, min_score, max_score, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_topics(db_path: str = None) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT topic_head, COUNT(*) as count, ROUND(AVG(solvability_score), 3) as avg_score
        FROM parts
        WHERE topic_head IS NOT NULL
        GROUP BY topic_head
        ORDER BY count DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def store_generated_item(item, db_path: str = None):
    """Persist a GeneratedItem to the database."""
    import json
    from datetime import datetime
    conn = get_connection(db_path)
    vr = item.verifier_result.model_dump() if item.verifier_result else None
    qr = item.quality_result.model_dump() if item.quality_result else None
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO generated_items
            (item_id, source, topic, primary_skill, secondary_skills,
             question_text, parts, canonical_solution, final_answer, answer_type,
             significant_steps, marks, parameters, verifier_result, quality_result,
             status, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        item.item_id, item.source, item.topic, item.primary_skill,
        json.dumps(item.secondary_skills),
        item.question_text,
        json.dumps([p.model_dump() for p in item.parts]),
        json.dumps(item.canonical_solution),
        item.final_answer, item.answer_type,
        item.significant_steps, item.marks,
        json.dumps(item.parameters),
        json.dumps(vr) if vr else None,
        json.dumps(qr) if qr else None,
        item.status,
        item.created_at or now,
        now,
    ))
    conn.commit()
    conn.close()


def load_generated_item(item_id: str, db_path: str = None):
    """Load a GeneratedItem from the database."""
    import json
    from schemas import GeneratedItem, QuestionPart, VerifierResult, QualityResult
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM generated_items WHERE item_id=?", (item_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    parts = [QuestionPart(**p) for p in json.loads(d.get("parts") or "[]")]
    vr = VerifierResult(**json.loads(d["verifier_result"])) if d.get("verifier_result") else None
    qr = QualityResult(**json.loads(d["quality_result"])) if d.get("quality_result") else None
    return GeneratedItem(
        item_id=d["item_id"], source=d["source"], topic=d["topic"],
        primary_skill=d["primary_skill"],
        secondary_skills=json.loads(d.get("secondary_skills") or "[]"),
        question_text=d["question_text"],
        parts=parts,
        canonical_solution=json.loads(d.get("canonical_solution") or "[]"),
        final_answer=d["final_answer"], answer_type=d["answer_type"],
        significant_steps=d["significant_steps"], marks=d["marks"],
        parameters=json.loads(d.get("parameters") or "{}"),
        verifier_result=vr, quality_result=qr,
        status=d["status"],
        created_at=d.get("created_at", ""), updated_at=d.get("updated_at", ""),
    )


def store_attempt(attempt, db_path: str = None):
    import json
    conn = get_connection(db_path)
    conn.execute("""
        INSERT OR REPLACE INTO student_attempts
            (attempt_id, user_id, item_id, submitted_answer, normalized_answer,
             is_correct, time_seconds, hints_used, detected_misconceptions, timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (
        attempt.attempt_id, attempt.user_id, attempt.item_id,
        attempt.submitted_answer, attempt.submitted_answer.strip().lower(),
        1 if attempt.is_correct else 0,
        attempt.time_seconds, attempt.hints_used,
        json.dumps(attempt.detected_misconceptions),
        attempt.timestamp,
    ))
    # Update item_stats
    conn.execute("""
        INSERT INTO item_stats (item_id, attempts, correct, p_correct, updated_at)
        VALUES (?, 1, ?, ?, ?)
        ON CONFLICT(item_id) DO UPDATE SET
            attempts = attempts + 1,
            correct  = correct + excluded.correct,
            p_correct = CAST(correct + excluded.correct AS REAL) / (attempts + 1),
            updated_at = excluded.updated_at
    """, (attempt.item_id, 1 if attempt.is_correct else 0,
          1.0 if attempt.is_correct else 0.0, attempt.timestamp))
    conn.commit()
    conn.close()


# ─── Users ────────────────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str, role: str, db_path: str = None) -> dict:
    import uuid
    from datetime import datetime
    conn = get_connection(db_path)
    user_id = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO users (user_id, username, password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, username, password_hash, role, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return {"user_id": user_id, "username": username, "role": role}


def get_user_by_username(username: str, db_path: str = None) -> dict | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_item_status(item_id: str, status: str, db_path: str = None) -> bool:
    from datetime import datetime
    conn = get_connection(db_path)
    cur = conn.execute(
        "UPDATE generated_items SET status = ?, updated_at = ? WHERE item_id = ?",
        (status, datetime.now().isoformat(), item_id))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ─── Saved papers ─────────────────────────────────────────────────────────────

def save_paper(owner_user_id: str, name: str, questions: list,
               saved_paper_id: str = None, db_path: str = None) -> str:
    import uuid
    from datetime import datetime
    conn = get_connection(db_path)
    now = datetime.now().isoformat()
    if saved_paper_id:
        cur = conn.execute("""
            UPDATE saved_papers SET name = ?, questions_json = ?, updated_at = ?
            WHERE saved_paper_id = ? AND owner_user_id = ?
        """, (name, json.dumps(questions), now, saved_paper_id, owner_user_id))
        if cur.rowcount == 0:
            conn.close()
            raise ValueError("Paper not found or not owned by user")
    else:
        saved_paper_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO saved_papers (saved_paper_id, owner_user_id, name, questions_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (saved_paper_id, owner_user_id, name, json.dumps(questions), now, now))
    conn.commit()
    conn.close()
    return saved_paper_id


def list_papers(owner_user_id: str, db_path: str = None) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT saved_paper_id, name, created_at, updated_at,
               json_array_length(questions_json) AS question_count
        FROM saved_papers WHERE owner_user_id = ?
        ORDER BY updated_at DESC
    """, (owner_user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_paper(saved_paper_id: str, owner_user_id: str, db_path: str = None) -> dict | None:
    conn = get_connection(db_path)
    row = conn.execute("""
        SELECT * FROM saved_papers WHERE saved_paper_id = ? AND owner_user_id = ?
    """, (saved_paper_id, owner_user_id)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["questions"] = json.loads(d.pop("questions_json"))
    return d


def delete_paper(saved_paper_id: str, owner_user_id: str, db_path: str = None) -> bool:
    conn = get_connection(db_path)
    cur = conn.execute(
        "DELETE FROM saved_papers WHERE saved_paper_id = ? AND owner_user_id = ?",
        (saved_paper_id, owner_user_id))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# ─── Classes & enrollment ─────────────────────────────────────────────────────

# Unambiguous alphabet for join codes (no 0/O, 1/I/L)
_JOIN_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def _new_join_code() -> str:
    import secrets
    return "".join(secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(6))


def create_class(teacher_id: str, name: str, level: str = None, db_path: str = None) -> dict:
    import uuid
    from datetime import datetime
    conn = get_connection(db_path)
    class_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    for _ in range(10):
        code = _new_join_code()
        try:
            conn.execute("""
                INSERT INTO classes (class_id, teacher_id, name, level, join_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (class_id, teacher_id, name, level, code, now))
            conn.commit()
            conn.close()
            return {"class_id": class_id, "teacher_id": teacher_id, "name": name,
                    "level": level, "join_code": code, "created_at": now}
        except sqlite3.IntegrityError:
            continue  # join_code collision — retry with a new code
    conn.close()
    raise RuntimeError("Could not allocate a unique join code")


def get_class(class_id: str, db_path: str = None) -> dict | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM classes WHERE class_id = ?", (class_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_class_by_join_code(join_code: str, db_path: str = None) -> dict | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM classes WHERE join_code = ?",
                       (join_code.strip().upper(),)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_classes_for_teacher(teacher_id: str, db_path: str = None) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT c.*,
               (SELECT COUNT(*) FROM enrollments e WHERE e.class_id = c.class_id) AS student_count,
               (SELECT COUNT(*) FROM assignments a WHERE a.class_id = c.class_id) AS assignment_count
        FROM classes c WHERE c.teacher_id = ?
        ORDER BY c.created_at DESC
    """, (teacher_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_classes_for_student(student_id: str, db_path: str = None) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT c.class_id, c.name, c.level, c.created_at, e.joined_at,
               u.username AS teacher_name,
               (SELECT COUNT(*) FROM assignments a WHERE a.class_id = c.class_id) AS assignment_count
        FROM enrollments e
        JOIN classes c ON c.class_id = e.class_id
        JOIN users u   ON u.user_id = c.teacher_id
        WHERE e.student_id = ?
        ORDER BY e.joined_at DESC
    """, (student_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def enroll_student(class_id: str, student_id: str, db_path: str = None) -> bool:
    from datetime import datetime
    conn = get_connection(db_path)
    try:
        conn.execute("INSERT INTO enrollments (class_id, student_id, joined_at) VALUES (?, ?, ?)",
                     (class_id, student_id, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # already enrolled
    finally:
        conn.close()


def unenroll_student(class_id: str, student_id: str, db_path: str = None) -> bool:
    conn = get_connection(db_path)
    cur = conn.execute("DELETE FROM enrollments WHERE class_id = ? AND student_id = ?",
                       (class_id, student_id))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def is_enrolled(class_id: str, student_id: str, db_path: str = None) -> bool:
    conn = get_connection(db_path)
    row = conn.execute("SELECT 1 FROM enrollments WHERE class_id = ? AND student_id = ?",
                       (class_id, student_id)).fetchone()
    conn.close()
    return row is not None


def list_roster(class_id: str, db_path: str = None) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT u.user_id, u.username, e.joined_at
        FROM enrollments e JOIN users u ON u.user_id = e.student_id
        WHERE e.class_id = ?
        ORDER BY u.username
    """, (class_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Assignments ──────────────────────────────────────────────────────────────

def create_assignment(class_id: str, title: str, questions: list, due_date: str = None,
                      settings: dict = None, db_path: str = None) -> dict:
    import uuid
    from datetime import datetime
    conn = get_connection(db_path)
    assignment_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO assignments (assignment_id, class_id, title, questions_json,
                                 due_date, settings_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (assignment_id, class_id, title, json.dumps(questions),
          due_date, json.dumps(settings or {}), now))
    conn.commit()
    conn.close()
    return {"assignment_id": assignment_id, "class_id": class_id, "title": title,
            "due_date": due_date, "created_at": now}


def get_assignment(assignment_id: str, db_path: str = None) -> dict | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM assignments WHERE assignment_id = ?",
                       (assignment_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["questions"] = json.loads(d.pop("questions_json"))
    d["settings"] = json.loads(d.pop("settings_json") or "{}")
    return d


def list_assignments(class_id: str, db_path: str = None) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT assignment_id, class_id, title, due_date, settings_json, created_at,
               json_array_length(questions_json) AS question_count,
               (SELECT COUNT(*) FROM submissions s
                WHERE s.assignment_id = assignments.assignment_id
                  AND s.status IN ('submitted','graded')) AS submission_count
        FROM assignments WHERE class_id = ?
        ORDER BY created_at DESC
    """, (class_id,)).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["settings"] = json.loads(d.pop("settings_json") or "{}")
        out.append(d)
    return out


# ─── Submissions ──────────────────────────────────────────────────────────────

def get_or_create_submission(assignment_id: str, student_id: str, db_path: str = None) -> dict:
    import uuid
    from datetime import datetime
    conn = get_connection(db_path)
    row = conn.execute("""
        SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?
    """, (assignment_id, student_id)).fetchone()
    if row:
        conn.close()
        return dict(row)
    submission_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO submissions (submission_id, assignment_id, student_id, status, started_at)
        VALUES (?, ?, ?, 'in_progress', ?)
    """, (submission_id, assignment_id, student_id, now))
    conn.commit()
    conn.close()
    return {"submission_id": submission_id, "assignment_id": assignment_id,
            "student_id": student_id, "status": "in_progress", "started_at": now,
            "submitted_at": None, "graded_at": None, "auto_total": None, "final_total": None}


def get_submission(submission_id: str, db_path: str = None) -> dict | None:
    conn = get_connection(db_path)
    row = conn.execute("SELECT * FROM submissions WHERE submission_id = ?",
                       (submission_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_submission_for_student(assignment_id: str, student_id: str, db_path: str = None) -> dict | None:
    conn = get_connection(db_path)
    row = conn.execute("""
        SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?
    """, (assignment_id, student_id)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_submissions_for_assignment(assignment_id: str, db_path: str = None) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT s.*, u.username AS student_name
        FROM submissions s JOIN users u ON u.user_id = s.student_id
        WHERE s.assignment_id = ?
        ORDER BY u.username
    """, (assignment_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def finalize_submission(submission_id: str, answers: list[dict], auto_total: float,
                        db_path: str = None):
    """Store graded answers and mark the submission as submitted."""
    import uuid
    from datetime import datetime
    conn = get_connection(db_path)
    now = datetime.now().isoformat()
    for a in answers:
        conn.execute("""
            INSERT OR REPLACE INTO submission_answers
                (answer_id, submission_id, question_index, submitted_answer,
                 is_correct, auto_score, max_score, teacher_score, teacher_comment,
                 detected_misconceptions)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?)
        """, (str(uuid.uuid4()), submission_id, a["question_index"],
              a["submitted_answer"], 1 if a["is_correct"] else 0,
              a["auto_score"], a["max_score"],
              json.dumps(a.get("detected_misconceptions", []))))
    conn.execute("""
        UPDATE submissions SET status = 'submitted', submitted_at = ?, auto_total = ?
        WHERE submission_id = ?
    """, (now, auto_total, submission_id))
    conn.commit()
    conn.close()


def get_submission_answers(submission_id: str, db_path: str = None) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT * FROM submission_answers WHERE submission_id = ?
        ORDER BY question_index
    """, (submission_id,)).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["detected_misconceptions"] = json.loads(d.get("detected_misconceptions") or "[]")
        out.append(d)
    return out


def apply_teacher_grades(submission_id: str, overrides: list[dict], final_total: float,
                         db_path: str = None):
    """Apply per-answer teacher overrides/comments and mark the submission graded."""
    from datetime import datetime
    conn = get_connection(db_path)
    for o in overrides:
        conn.execute("""
            UPDATE submission_answers
            SET teacher_score = ?, teacher_comment = ?
            WHERE submission_id = ? AND question_index = ?
        """, (o.get("teacher_score"), o.get("teacher_comment"),
              submission_id, o["question_index"]))
    conn.execute("""
        UPDATE submissions SET status = 'graded', graded_at = ?, final_total = ?
        WHERE submission_id = ?
    """, (datetime.now().isoformat(), final_total, submission_id))
    conn.commit()
    conn.close()


def get_stats(db_path: str = None) -> dict:
    conn = get_connection(db_path)
    papers  = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    questions = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    parts   = conn.execute("SELECT COUNT(*) FROM parts").fetchone()[0]
    conn.close()
    return {"papers": papers, "questions": questions, "parts": parts}
