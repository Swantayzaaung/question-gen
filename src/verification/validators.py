"""Input validators for API routes."""

VALID_CLEANLINESS = {"clean", "mixed", "messy"}
VALID_FOCUS = {"single", "multi"}
VALID_STEPS = {1, 2, 3, 4, 5}


def validate_generate_input(data: dict) -> list[str]:
    errors = []
    if not data.get("topic"):
        errors.append("topic is required")
    steps = data.get("steps", 2)
    try:
        steps = int(steps)
        if steps not in VALID_STEPS:
            errors.append(f"steps must be one of {sorted(VALID_STEPS)}")
    except (TypeError, ValueError):
        errors.append("steps must be an integer")
    cleanliness = data.get("cleanliness", "clean")
    if cleanliness not in VALID_CLEANLINESS:
        errors.append(f"cleanliness must be one of {sorted(VALID_CLEANLINESS)}")
    focus = data.get("focus", "single")
    if focus not in VALID_FOCUS:
        errors.append(f"focus must be one of {sorted(VALID_FOCUS)}")
    return errors


def validate_attempt_input(data: dict) -> list[str]:
    errors = []
    if not data.get("user_id"):
        errors.append("user_id is required")
    if not data.get("item_id"):
        errors.append("item_id is required")
    if "submitted_answer" not in data:
        errors.append("submitted_answer is required")
    return errors
