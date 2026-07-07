"""
Grading blueprint: student submissions, auto-grading, teacher override + publish.

Lifecycle: in_progress → submitted (auto-graded) → graded (teacher published).
Students see teacher scores/comments only once status is 'graded'.
"""

from __future__ import annotations
from datetime import datetime

from flask import Blueprint, request, jsonify, session

from database import (get_assignment, get_class,
                      get_or_create_submission, get_submission,
                      get_submission_for_student, list_submissions_for_assignment,
                      finalize_submission, get_submission_answers, apply_teacher_grades)
from authz import (student_required, teacher_required,
                   assignment_for_teacher_or_error, assignment_for_student_or_error)
from services.grading import grade_submission

bp = Blueprint("grading", __name__)


def _solutions_visible(assignment: dict, submission: dict) -> bool:
    if submission["status"] == "graded":
        return True
    return (submission["status"] == "submitted"
            and assignment["settings"].get("show_solutions_after_submit", True))


def _answer_view_for_student(ans: dict, graded: bool) -> dict:
    view = {
        "question_index": ans["question_index"],
        "submitted_answer": ans["submitted_answer"],
        "is_correct": bool(ans["is_correct"]),
        "auto_score": ans["auto_score"],
        "max_score": ans["max_score"],
        "detected_misconceptions": ans["detected_misconceptions"],
    }
    if graded:
        view["teacher_score"] = ans["teacher_score"]
        view["teacher_comment"] = ans["teacher_comment"]
        view["final_score"] = (ans["teacher_score"]
                               if ans["teacher_score"] is not None else ans["auto_score"])
    return view


# ─── Student: submit ──────────────────────────────────────────────────────────

@bp.route("/assignments/<assignment_id>/submit", methods=["POST"])
@student_required
def submit_assignment(assignment_id):
    a, err = assignment_for_student_or_error(assignment_id)
    if err:
        return err

    if a["due_date"] and not a["settings"].get("allow_late", True):
        try:
            if datetime.now() > datetime.fromisoformat(a["due_date"]):
                return jsonify({"error": "This assignment is past its due date"}), 403
        except ValueError:
            pass  # unparseable due date — don't lock students out

    data = request.get_json(silent=True) or {}
    answers = data.get("answers")
    if not isinstance(answers, list):
        return jsonify({"error": "answers must be a list"}), 400

    sub = get_or_create_submission(assignment_id, session["user_id"])
    if sub["status"] != "in_progress":
        return jsonify({"error": "You have already submitted this assignment"}), 409

    results, auto_total = grade_submission(a["questions"], [str(x or "") for x in answers])
    finalize_submission(sub["submission_id"], results, auto_total)

    # Feed the mastery model (best-effort; grading must not fail on this)
    try:
        from adaptation.mastery import update_mastery
        for i, q in enumerate(a["questions"]):
            skill = q.get("primary_skill") or q.get("topic")
            if skill:
                update_mastery(session["user_id"], skill, results[i]["is_correct"])
    except Exception:
        pass

    max_total = sum(r["max_score"] for r in results)
    response = {
        "submission_id": sub["submission_id"],
        "status": "submitted",
        "auto_total": auto_total,
        "max_total": max_total,
        "answers": [_answer_view_for_student(dict(r, teacher_score=None, teacher_comment=None,
                                                  detected_misconceptions=r["detected_misconceptions"]),
                                             graded=False)
                    for r in results],
    }
    if _solutions_visible(a, {"status": "submitted"}):
        response["solutions"] = [{"question_index": i,
                                  "final_answer": q.get("final_answer"),
                                  "worked_solution": q.get("worked_solution")
                                  or q.get("canonical_solution") or []}
                                 for i, q in enumerate(a["questions"])]
    return jsonify(response)


# ─── Teacher: review submissions ──────────────────────────────────────────────

@bp.route("/assignments/<assignment_id>/submissions", methods=["GET"])
@teacher_required
def submissions_list(assignment_id):
    a, err = assignment_for_teacher_or_error(assignment_id)
    if err:
        return err
    subs = list_submissions_for_assignment(assignment_id)
    max_total = sum(sum(p.get("marks", 0) or 0 for p in q.get("parts") or []) or 1
                    for q in a["questions"])
    return jsonify({"assignment_id": assignment_id, "title": a["title"],
                    "max_total": max_total, "submissions": subs})


@bp.route("/submissions/<submission_id>", methods=["GET"])
def submission_detail(submission_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    sub = get_submission(submission_id)
    if not sub:
        return jsonify({"error": "Submission not found"}), 404
    a = get_assignment(sub["assignment_id"])

    if session.get("role") == "teacher":
        cls = get_class(a["class_id"])
        if not cls or cls["teacher_id"] != session["user_id"]:
            return jsonify({"error": "Not your class"}), 403
        answers = get_submission_answers(submission_id)
        return jsonify({"submission": sub, "answers": answers,
                        "questions": a["questions"], "title": a["title"]})

    # Student: own submission only
    if sub["student_id"] != session["user_id"]:
        return jsonify({"error": "Not your submission"}), 403
    graded = sub["status"] == "graded"
    answers = [_answer_view_for_student(ans, graded)
               for ans in get_submission_answers(submission_id)]
    out = {"submission": {k: sub[k] for k in ("submission_id", "assignment_id", "status",
                                              "submitted_at", "auto_total")},
           "answers": answers, "title": a["title"],
           "questions": [{"question_index": i, "question_text": q.get("question_text"),
                          "parts": q.get("parts") or []}
                         for i, q in enumerate(a["questions"])]}
    if graded:
        out["submission"]["final_total"] = sub["final_total"]
        out["submission"]["graded_at"] = sub["graded_at"]
    if _solutions_visible(a, sub):
        out["solutions"] = [{"question_index": i,
                             "final_answer": q.get("final_answer"),
                             "worked_solution": q.get("worked_solution")
                             or q.get("canonical_solution") or []}
                            for i, q in enumerate(a["questions"])]
    return jsonify(out)


@bp.route("/submissions/<submission_id>/grade", methods=["POST"])
@teacher_required
def grade_submission_route(submission_id):
    sub = get_submission(submission_id)
    if not sub:
        return jsonify({"error": "Submission not found"}), 404
    a = get_assignment(sub["assignment_id"])
    cls = get_class(a["class_id"])
    if not cls or cls["teacher_id"] != session["user_id"]:
        return jsonify({"error": "Not your class"}), 403
    if sub["status"] == "in_progress":
        return jsonify({"error": "Student has not submitted yet"}), 409

    data = request.get_json(silent=True) or {}
    overrides = data.get("overrides") or []

    existing = {ans["question_index"]: ans for ans in get_submission_answers(submission_id)}
    clean = []
    for o in overrides:
        idx = o.get("question_index")
        if idx not in existing:
            return jsonify({"error": f"No answer at question_index {idx}"}), 400
        score = o.get("teacher_score")
        if score is not None:
            try:
                score = float(score)
            except (TypeError, ValueError):
                return jsonify({"error": f"Invalid teacher_score at index {idx}"}), 400
            if not (0 <= score <= existing[idx]["max_score"]):
                return jsonify({"error": f"teacher_score at index {idx} must be between "
                                         f"0 and {existing[idx]['max_score']}"}), 400
        comment = o.get("teacher_comment")
        clean.append({"question_index": idx, "teacher_score": score,
                      "teacher_comment": str(comment) if comment else None})

    # Final total: teacher override where present (incl. this batch), else auto score
    batch = {c["question_index"]: c for c in clean}
    final_total = 0.0
    for idx, ans in existing.items():
        if idx in batch and batch[idx]["teacher_score"] is not None:
            final_total += batch[idx]["teacher_score"]
        elif idx not in batch and ans["teacher_score"] is not None:
            final_total += ans["teacher_score"]
        else:
            final_total += ans["auto_score"]

    apply_teacher_grades(submission_id, clean, final_total)
    return jsonify({"submission_id": submission_id, "status": "graded",
                    "final_total": final_total})
