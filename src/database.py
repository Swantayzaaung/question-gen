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

        CREATE INDEX IF NOT EXISTS idx_gen_items_topic   ON generated_items(topic);
        CREATE INDEX IF NOT EXISTS idx_gen_items_skill   ON generated_items(primary_skill);
        CREATE INDEX IF NOT EXISTS idx_gen_items_status  ON generated_items(status);
        CREATE INDEX IF NOT EXISTS idx_attempts_user     ON student_attempts(user_id);
        CREATE INDEX IF NOT EXISTS idx_attempts_item     ON student_attempts(item_id);
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


def get_stats(db_path: str = None) -> dict:
    conn = get_connection(db_path)
    papers  = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    questions = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    parts   = conn.execute("SELECT COUNT(*) FROM parts").fetchone()[0]
    conn.close()
    return {"papers": papers, "questions": questions, "parts": parts}
