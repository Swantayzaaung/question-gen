"""Papers blueprint: teacher-owned saved papers + printable paper export."""

from __future__ import annotations

from flask import Blueprint, request, jsonify, session, render_template

from database import save_paper, list_papers, load_paper, delete_paper
from authz import teacher_required

bp = Blueprint("papers", __name__)


@bp.route("/papers", methods=["GET"])
@teacher_required
def papers_list():
    return jsonify(list_papers(session["user_id"]))


@bp.route("/papers", methods=["POST"])
@teacher_required
def papers_save():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    questions = data.get("questions", [])
    if not name:
        return jsonify({"error": "Paper name required"}), 400
    if not isinstance(questions, list) or not questions:
        return jsonify({"error": "Paper must contain at least one question"}), 400
    try:
        pid = save_paper(session["user_id"], name, questions,
                         saved_paper_id=data.get("saved_paper_id"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify({"saved_paper_id": pid, "name": name})


@bp.route("/papers/<saved_paper_id>", methods=["GET"])
@teacher_required
def papers_load(saved_paper_id):
    paper = load_paper(saved_paper_id, session["user_id"])
    if not paper:
        return jsonify({"error": "Paper not found"}), 404
    return jsonify(paper)


@bp.route("/papers/<saved_paper_id>", methods=["DELETE"])
@teacher_required
def papers_delete(saved_paper_id):
    if not delete_paper(saved_paper_id, session["user_id"]):
        return jsonify({"error": "Paper not found"}), 404
    return jsonify({"ok": True})


@bp.route("/paper/print", methods=["POST"])
def paper_print():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    questions = data.get("questions", [])
    config = data.get("config", {})
    for q in questions:
        q["total_marks"] = sum(p.get("marks", 0) for p in q.get("parts", []))
    total_marks = sum(q["total_marks"] for q in questions)
    return render_template("paper_print.html", questions=questions, config=config,
                           total_marks=total_marks)
