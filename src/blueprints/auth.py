"""Auth blueprint: register / login / logout / me. URLs unchanged from the pre-blueprint app."""

from __future__ import annotations
import re

from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

from database import create_user, get_user_by_username

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _login(user: dict):
    session.permanent = True
    session["user_id"] = user["user_id"]
    session["username"] = user["username"]
    session["role"] = user["role"]


@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    role = data.get("role", "student")

    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        return jsonify({"error": "Username must be 3-32 characters (letters, digits, _ . -)"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if role not in ("teacher", "student"):
        return jsonify({"error": "Role must be teacher or student"}), 400
    if get_user_by_username(username):
        return jsonify({"error": "Username already taken"}), 409

    user = create_user(username, generate_password_hash(password), role)
    _login(user)
    return jsonify(user)


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    user = get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid username or password"}), 401

    _login(user)
    return jsonify({"user_id": user["user_id"], "username": user["username"], "role": user["role"]})


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.route("/me")
def me():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({"user_id": session["user_id"], "username": session["username"],
                    "role": session["role"]})
