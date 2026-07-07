"""
Classroom blueprint: classes, enrollment, assignments.

Authorization model:
  - Teachers operate only on classes they own (owned_class_or_error).
  - Students operate only on classes they're enrolled in.
  - Students never see canonical answers for questions they haven't submitted.
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify, session, render_template

from database import (create_class, get_class, get_class_by_join_code,
                      list_classes_for_teacher, list_classes_for_student,
                      enroll_student, unenroll_student, is_enrolled, list_roster,
                      create_assignment, get_assignment, list_assignments,
                      get_submission_for_student, load_paper)
from authz import (login_required, teacher_required, student_required,
                   owned_class_or_error, assignment_for_teacher_or_error,
                   assignment_for_student_or_error)

bp = Blueprint("classroom", __name__)

# Keys stripped from question snapshots before students see them
_ANSWER_KEYS = ("final_answer", "worked_solution", "canonical_solution", "verifier_result",
                "quality_result", "notes")


def sanitize_question_for_student(q: dict) -> dict:
    return {k: v for k, v in q.items() if k not in _ANSWER_KEYS}


@bp.route("/classroom")
def classroom_page():
    return render_template("classroom.html")


@bp.route("/assignment/<assignment_id>")
def assignment_page(assignment_id):
    return render_template("assignment.html", assignment_id=assignment_id)


# ─── Classes ──────────────────────────────────────────────────────────────────

@bp.route("/classes", methods=["POST"])
@teacher_required
def classes_create():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    level = str(data.get("level", "")).strip() or None
    if not name or len(name) > 80:
        return jsonify({"error": "Class name required (max 80 characters)"}), 400
    cls = create_class(session["user_id"], name, level)
    return jsonify(cls)


@bp.route("/classes", methods=["GET"])
@login_required
def classes_list():
    if session.get("role") == "teacher":
        return jsonify(list_classes_for_teacher(session["user_id"]))
    return jsonify(list_classes_for_student(session["user_id"]))


@bp.route("/classes/join", methods=["POST"])
@student_required
def classes_join():
    data = request.get_json(silent=True) or {}
    code = str(data.get("join_code", "")).strip()
    if not code:
        return jsonify({"error": "Join code required"}), 400
    cls = get_class_by_join_code(code)
    if not cls:
        return jsonify({"error": "No class found for that code"}), 404
    newly = enroll_student(cls["class_id"], session["user_id"])
    return jsonify({"class_id": cls["class_id"], "name": cls["name"],
                    "level": cls["level"], "already_enrolled": not newly})


@bp.route("/classes/<class_id>", methods=["GET"])
@login_required
def classes_detail(class_id):
    if session.get("role") == "teacher":
        cls, err = owned_class_or_error(class_id)
        if err:
            return err
        cls["roster"] = list_roster(class_id)
        cls["assignments"] = list_assignments(class_id)
        return jsonify(cls)

    # Student: must be enrolled; hide the join code and other students
    if not is_enrolled(class_id, session["user_id"]):
        return jsonify({"error": "Not enrolled in this class"}), 403
    cls = get_class(class_id)
    assignments = list_assignments(class_id)
    for a in assignments:
        sub = get_submission_for_student(a["assignment_id"], session["user_id"])
        a["my_submission_status"] = sub["status"] if sub else None
        a["my_final_total"] = sub.get("final_total") if sub else None
        a["my_auto_total"] = sub.get("auto_total") if sub else None
    return jsonify({"class_id": cls["class_id"], "name": cls["name"], "level": cls["level"],
                    "assignments": assignments})


@bp.route("/classes/<class_id>/students/<student_id>", methods=["DELETE"])
@teacher_required
def classes_remove_student(class_id, student_id):
    _, err = owned_class_or_error(class_id)
    if err:
        return err
    if not unenroll_student(class_id, student_id):
        return jsonify({"error": "Student not enrolled"}), 404
    return jsonify({"ok": True})


# ─── Assignments ──────────────────────────────────────────────────────────────

@bp.route("/classes/<class_id>/assignments", methods=["POST"])
@teacher_required
def assignments_create(class_id):
    _, err = owned_class_or_error(class_id)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    if not title:
        return jsonify({"error": "Assignment title required"}), 400

    # Questions come either inline or from a saved paper (snapshot either way)
    questions = data.get("questions")
    if not questions and data.get("saved_paper_id"):
        paper = load_paper(data["saved_paper_id"], session["user_id"])
        if not paper:
            return jsonify({"error": "Saved paper not found"}), 404
        questions = paper["questions"]
    if not isinstance(questions, list) or not questions:
        return jsonify({"error": "Assignment needs at least one question"}), 400

    settings = data.get("settings") or {}
    settings.setdefault("show_solutions_after_submit", True)
    settings.setdefault("allow_late", True)

    unreviewed = sum(1 for q in questions
                     if q.get("status") not in ("approved", "verified"))

    a = create_assignment(class_id, title, questions,
                          due_date=data.get("due_date") or None, settings=settings)
    a["question_count"] = len(questions)
    a["unreviewed_count"] = unreviewed
    if unreviewed:
        a["warning"] = (f"{unreviewed} question(s) have not been approved/verified. "
                        "Consider reviewing them before students take this assignment.")
    return jsonify(a)


@bp.route("/assignments/<assignment_id>", methods=["GET"])
@login_required
def assignment_detail(assignment_id):
    if session.get("role") == "teacher":
        a, err = assignment_for_teacher_or_error(assignment_id)
        if err:
            return err
        return jsonify(a)

    a, err = assignment_for_student_or_error(assignment_id)
    if err:
        return err
    sub = get_submission_for_student(assignment_id, session["user_id"])
    return jsonify({
        "assignment_id": a["assignment_id"],
        "class_id": a["class_id"],
        "title": a["title"],
        "due_date": a["due_date"],
        "settings": {"show_solutions_after_submit":
                     a["settings"].get("show_solutions_after_submit", True)},
        "questions": [sanitize_question_for_student(q) for q in a["questions"]],
        "my_submission_status": sub["status"] if sub else None,
        "my_submission_id": sub["submission_id"] if sub else None,
    })
