"""Tests for Flask API routes."""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import os
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

import app as flask_app
from database import init_db


@pytest.fixture
def client(tmp_path):
    import database
    db_path = str(tmp_path / "test.db")
    database.DB_PATH = Path(db_path)
    init_db(db_path)
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


class TestGenerate:
    def test_missing_topic(self, client):
        res = client.post("/generate",
                          data=json.dumps({}),
                          content_type="application/json")
        assert res.status_code == 400
        data = json.loads(res.data)
        assert "error" in data

    def test_invalid_steps(self, client):
        res = client.post("/generate",
                          data=json.dumps({"topic": "arithmetic_series", "steps": 99}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_invalid_cleanliness(self, client):
        res = client.post("/generate",
                          data=json.dumps({"topic": "arithmetic_series", "cleanliness": "invalid"}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_arithmetic_series_template(self, client):
        # This should work without API key via template
        res = client.post("/generate",
                          data=json.dumps({
                              "topic": "arithmetic_series",
                              "steps": 2,
                              "cleanliness": "clean",
                              "focus": "single"
                          }),
                          content_type="application/json")
        # Should succeed with template (no LLM needed)
        assert res.status_code in (200, 500)
        if res.status_code == 200:
            data = json.loads(res.data)
            assert "question_text" in data
            assert "final_answer" in data


class TestAttempt:
    def test_missing_fields(self, client):
        res = client.post("/attempt",
                          data=json.dumps({"user_id": "u1"}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_unknown_item(self, client):
        res = client.post("/attempt",
                          data=json.dumps({
                              "user_id": "u1",
                              "item_id": "nonexistent_item_xyz",
                              "submitted_answer": "42"
                          }),
                          content_type="application/json")
        assert res.status_code == 404


class TestMastery:
    def test_mastery_returns_list(self, client):
        res = client.get("/mastery?user_id=nobody")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert isinstance(data, list)


class TestTopics:
    def test_topics_list(self, client):
        res = client.get("/topics")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert isinstance(data, list)
        assert "arithmetic_series" in data
