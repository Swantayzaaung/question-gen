"""
Authorization helpers shared across blueprints.

Role decorators return JSON errors (401 not logged in / 403 wrong role).
Resource-scoped helpers fetch the object AND verify ownership/enrollment in
one step so routes can't forget the check.
"""

from __future__ import annotations
from functools import wraps

from flask import session, jsonify

from database import get_class, get_assignment, is_enrolled


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401
        return f(*args, **kwargs)
    return wrapper


def teacher_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401
        if session.get("role") != "teacher":
            return jsonify({"error": "Teacher account required"}), 403
        return f(*args, **kwargs)
    return wrapper


def student_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Login required"}), 401
        if session.get("role") != "student":
            return jsonify({"error": "Student account required"}), 403
        return f(*args, **kwargs)
    return wrapper


def current_user_id() -> str | None:
    return session.get("user_id")


def owned_class_or_error(class_id: str):
    """Return (class_dict, None) if the logged-in teacher owns it, else (None, response)."""
    cls = get_class(class_id)
    if not cls:
        return None, (jsonify({"error": "Class not found"}), 404)
    if cls["teacher_id"] != session.get("user_id"):
        return None, (jsonify({"error": "Not your class"}), 403)
    return cls, None


def assignment_for_teacher_or_error(assignment_id: str):
    """Return (assignment, None) if the logged-in teacher owns its class."""
    a = get_assignment(assignment_id)
    if not a:
        return None, (jsonify({"error": "Assignment not found"}), 404)
    cls = get_class(a["class_id"])
    if not cls or cls["teacher_id"] != session.get("user_id"):
        return None, (jsonify({"error": "Not your assignment"}), 403)
    return a, None


def assignment_for_student_or_error(assignment_id: str):
    """Return (assignment, None) if the logged-in student is enrolled in its class."""
    a = get_assignment(assignment_id)
    if not a:
        return None, (jsonify({"error": "Assignment not found"}), 404)
    if not is_enrolled(a["class_id"], session.get("user_id")):
        return None, (jsonify({"error": "Not enrolled in this class"}), 403)
    return a, None
