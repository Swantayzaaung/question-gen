"""Generation blueprint: question generation, practice attempts, item review, mastery."""

from __future__ import annotations
import uuid

from flask import Blueprint, request, jsonify, session, render_template

from generator import generate_question, list_topics, PRESETS
from database import load_generated_item, store_attempt, update_item_status
from verification.validators import validate_generate_input, validate_attempt_input
from verification.sympy_tools import equivalent
from authz import teacher_required

bp = Blueprint("generation", __name__)


@bp.route("/")
def index():
    topics = list_topics()
    topic_labels = {t: t.replace("_", " ").title() for t in topics}
    return render_template("index.html", topics=topics, topic_labels=topic_labels, presets=PRESETS)


@bp.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    errors = validate_generate_input(data)
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    topic = data["topic"]
    steps = int(data.get("steps", 2))
    cleanliness = data.get("cleanliness", "clean")
    focus = data.get("focus", "single")

    result = generate_question(topic, steps=steps, cleanliness=cleanliness,
                               focus=focus, max_attempts=3)
    if result is None:
        return jsonify({"error": "Generation failed"}), 500

    return jsonify(result)


@bp.route("/attempt", methods=["POST"])
def attempt():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    errors = validate_attempt_input(data)
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    # Prefer the logged-in identity; fall back to the client-supplied id for anonymous use
    user_id = session.get("user_id") or data["user_id"]
    item_id = data["item_id"]
    submitted = str(data["submitted_answer"]).strip()
    time_seconds = data.get("time_seconds")
    hints_used = int(data.get("hints_used", 0))

    item = load_generated_item(item_id)
    if not item:
        return jsonify({"error": f"Item {item_id} not found"}), 404

    is_correct = equivalent(submitted, item.final_answer)

    from pedagogy.misconception_tags import detect_misconceptions
    misconceptions = detect_misconceptions(item, submitted)

    from schemas import LearnerAttempt
    att = LearnerAttempt(
        attempt_id=str(uuid.uuid4()),
        user_id=user_id,
        item_id=item_id,
        submitted_answer=submitted,
        is_correct=is_correct,
        time_seconds=float(time_seconds) if time_seconds is not None else None,
        hints_used=hints_used,
        detected_misconceptions=misconceptions,
    )
    store_attempt(att)

    from adaptation.mastery import update_mastery
    mastery_state = update_mastery(user_id, item.primary_skill, is_correct, hints_used)

    from adaptation.scheduler import recommend_next_items
    recs = recommend_next_items(user_id, n=3)

    feedback = "Correct!" if is_correct else f"Incorrect. The answer was {item.final_answer}."
    if misconceptions:
        feedback += f" Possible issues: {', '.join(misconceptions)}."

    return jsonify({
        "is_correct": is_correct,
        "correct_answer": item.final_answer,
        "feedback": feedback,
        "detected_misconceptions": misconceptions,
        "mastery": mastery_state.model_dump(),
        "recommendations": recs,
    })


@bp.route("/recommendations")
def recommendations():
    user_id = session.get("user_id") or request.args.get("user_id", "default")
    n = int(request.args.get("n", 5))
    from adaptation.scheduler import recommend_next_items
    return jsonify(recommend_next_items(user_id, n=n))


@bp.route("/mastery")
def mastery():
    user_id = session.get("user_id") or request.args.get("user_id", "default")
    from adaptation.mastery import get_all_mastery
    states = get_all_mastery(user_id)
    return jsonify([s.model_dump() for s in states])


@bp.route("/item/<item_id>")
def get_item(item_id):
    item = load_generated_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    if item.status not in ("approved", "verified"):
        return jsonify({"error": "Item not approved for serving"}), 403
    return jsonify(item.to_api_dict())


@bp.route("/item/<item_id>/review", methods=["POST"])
@teacher_required
def review_item(item_id):
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if action not in ("approve", "reject"):
        return jsonify({"error": "action must be 'approve' or 'reject'"}), 400
    new_status = "approved" if action == "approve" else "rejected"
    if not update_item_status(item_id, new_status):
        return jsonify({"error": "Item not found"}), 404
    return jsonify({"item_id": item_id, "status": new_status})


@bp.route("/topics")
def topics():
    return jsonify(list_topics())
