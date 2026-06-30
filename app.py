import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv(override=True)

from generator import generate_question, list_topics, PRESETS
from database import init_db, load_generated_item, store_attempt, get_connection
from verification.validators import validate_generate_input, validate_attempt_input
from verification.sympy_tools import equivalent

init_db()

app = Flask(__name__)

_DEV = os.environ.get("FLASK_ENV", "production") == "development"


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


@app.route("/")
def index():
    topics = list_topics()
    topic_labels = {t: t.replace("_", " ").title() for t in topics}
    return render_template("index.html", topics=topics, topic_labels=topic_labels, presets=PRESETS)


@app.route("/generate", methods=["POST"])
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


@app.route("/attempt", methods=["POST"])
def attempt():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    errors = validate_attempt_input(data)
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    user_id = data["user_id"]
    item_id = data["item_id"]
    submitted = str(data["submitted_answer"]).strip()
    time_seconds = data.get("time_seconds")
    hints_used = int(data.get("hints_used", 0))

    # Load item
    item = load_generated_item(item_id)
    if not item:
        return jsonify({"error": f"Item {item_id} not found"}), 404

    # Check correctness
    is_correct = equivalent(submitted, item.final_answer)

    # Detect misconceptions
    from pedagogy.misconception_tags import detect_misconceptions
    misconceptions = detect_misconceptions(item, submitted)

    # Store attempt
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

    # Update mastery
    from adaptation.mastery import update_mastery
    from skills import SKILLS
    skill_id = item.primary_skill
    mastery_state = update_mastery(user_id, skill_id, is_correct, hints_used)

    # Next recommendation
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


@app.route("/recommendations")
def recommendations():
    user_id = request.args.get("user_id", "default")
    n = int(request.args.get("n", 5))
    from adaptation.scheduler import recommend_next_items
    recs = recommend_next_items(user_id, n=n)
    return jsonify(recs)


@app.route("/mastery")
def mastery():
    user_id = request.args.get("user_id", "default")
    from adaptation.mastery import get_all_mastery
    states = get_all_mastery(user_id)
    return jsonify([s.model_dump() for s in states])


@app.route("/item/<item_id>")
def get_item(item_id):
    item = load_generated_item(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    if item.status not in ("approved", "verified"):
        return jsonify({"error": "Item not approved for serving"}), 403
    return jsonify(item.to_api_dict())


@app.route("/topics")
def topics():
    return jsonify(list_topics())


@app.route("/paper/print", methods=["POST"])
def paper_print():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    questions = data.get("questions", [])
    config = data.get("config", {})
    for q in questions:
        q["total_marks"] = sum(p.get("marks", 0) for p in q.get("parts", []))
    total_marks = sum(q["total_marks"] for q in questions)
    return render_template("paper_print.html", questions=questions, config=config, total_marks=total_marks)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=_DEV, port=port)
