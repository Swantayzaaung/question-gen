"""Tests for the classroom platform: classes, assignments, submissions, grading, authz."""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

import pytest

import app as flask_app
from database import init_db


QUESTIONS = [
    {"question_text": "Find $2+3$.",
     "parts": [{"part": "a", "instruction": "Evaluate.", "marks": 2}],
     "final_answer": "5", "worked_solution": ["Add the numbers."],
     "topic": "arithmetic_series", "status": "approved"},
    {"question_text": "Simplify $10/4$.",
     "parts": [{"part": "a", "instruction": "Simplify fully.", "marks": 3}],
     "final_answer": "5/2", "worked_solution": ["Divide by 2."],
     "topic": "logarithms", "status": "needs_review"},
]


@pytest.fixture
def clients(tmp_path):
    import database
    database.DB_PATH = Path(tmp_path / "test.db")
    init_db(str(database.DB_PATH))
    flask_app.app.config["TESTING"] = True

    teacher = flask_app.app.test_client()
    student = flask_app.app.test_client()
    teacher.post("/auth/register", json={"username": "teach", "password": "secret1", "role": "teacher"})
    student.post("/auth/register", json={"username": "stud", "password": "secret1", "role": "student"})
    return teacher, student


def make_class(teacher):
    return teacher.post("/classes", json={"name": "P2 Class", "level": "IAL"}).get_json()


def make_assignment(teacher, class_id, settings=None):
    body = {"title": "HW1", "questions": QUESTIONS}
    if settings:
        body["settings"] = settings
    return teacher.post(f"/classes/{class_id}/assignments", json=body).get_json()


class TestClasses:
    def test_create_and_list(self, clients):
        teacher, _ = clients
        cls = make_class(teacher)
        assert len(cls["join_code"]) == 6
        listed = teacher.get("/classes").get_json()
        assert len(listed) == 1 and listed[0]["name"] == "P2 Class"

    def test_student_cannot_create_class(self, clients):
        _, student = clients
        res = student.post("/classes", json={"name": "Nope"})
        assert res.status_code == 403

    def test_join_case_insensitive(self, clients):
        teacher, student = clients
        cls = make_class(teacher)
        res = student.post("/classes/join", json={"join_code": cls["join_code"].lower()})
        assert res.status_code == 200
        assert res.get_json()["already_enrolled"] is False
        # Second join reports already enrolled, doesn't error
        res = student.post("/classes/join", json={"join_code": cls["join_code"]})
        assert res.get_json()["already_enrolled"] is True

    def test_bad_join_code(self, clients):
        _, student = clients
        res = student.post("/classes/join", json={"join_code": "XXXXXX"})
        assert res.status_code == 404

    def test_roster_and_remove(self, clients):
        teacher, student = clients
        cls = make_class(teacher)
        student.post("/classes/join", json={"join_code": cls["join_code"]})
        detail = teacher.get(f"/classes/{cls['class_id']}").get_json()
        assert len(detail["roster"]) == 1
        sid = detail["roster"][0]["user_id"]
        res = teacher.delete(f"/classes/{cls['class_id']}/students/{sid}")
        assert res.status_code == 200
        detail = teacher.get(f"/classes/{cls['class_id']}").get_json()
        assert detail["roster"] == []

    def test_cross_teacher_forbidden(self, clients):
        teacher, _ = clients
        cls = make_class(teacher)
        other = flask_app.app.test_client()
        other.post("/auth/register", json={"username": "other", "password": "secret1", "role": "teacher"})
        assert other.get(f"/classes/{cls['class_id']}").status_code == 403


class TestAssignments:
    def test_create_with_needs_review_warning(self, clients):
        teacher, _ = clients
        cls = make_class(teacher)
        a = make_assignment(teacher, cls["class_id"])
        assert a["unreviewed_count"] == 1
        assert "warning" in a

    def test_snapshot_immutability(self, clients):
        """Editing the saved paper after assigning must not change the assignment."""
        teacher, student = clients
        cls = make_class(teacher)
        # Assign via a saved paper
        pid = teacher.post("/papers", json={"name": "P", "questions": QUESTIONS}).get_json()["saved_paper_id"]
        a = teacher.post(f"/classes/{cls['class_id']}/assignments",
                         json={"title": "HW", "saved_paper_id": pid}).get_json()
        # Mutate the paper afterwards
        teacher.post("/papers", json={"name": "P", "saved_paper_id": pid,
                                      "questions": [{"question_text": "changed",
                                                     "parts": [], "final_answer": "0"}]})
        got = teacher.get(f"/assignments/{a['assignment_id']}").get_json()
        assert len(got["questions"]) == 2
        assert got["questions"][0]["final_answer"] == "5"

    def test_student_view_strips_answers(self, clients):
        teacher, student = clients
        cls = make_class(teacher)
        student.post("/classes/join", json={"join_code": cls["join_code"]})
        a = make_assignment(teacher, cls["class_id"])
        view = student.get(f"/assignments/{a['assignment_id']}").get_json()
        for q in view["questions"]:
            assert "final_answer" not in q
            assert "worked_solution" not in q

    def test_non_enrolled_student_forbidden(self, clients):
        teacher, _ = clients
        cls = make_class(teacher)
        a = make_assignment(teacher, cls["class_id"])
        outsider = flask_app.app.test_client()
        outsider.post("/auth/register", json={"username": "out", "password": "secret1", "role": "student"})
        assert outsider.get(f"/assignments/{a['assignment_id']}").status_code == 403
        assert outsider.post(f"/assignments/{a['assignment_id']}/submit",
                             json={"answers": []}).status_code == 403

    def test_anonymous_gets_401(self, clients):
        teacher, _ = clients
        cls = make_class(teacher)
        a = make_assignment(teacher, cls["class_id"])
        anon = flask_app.app.test_client()
        assert anon.get(f"/assignments/{a['assignment_id']}").status_code == 401
        assert anon.get("/classes").status_code == 401


class TestSubmissionAndGrading:
    def _submit(self, clients, answers, settings=None):
        teacher, student = clients
        cls = make_class(teacher)
        student.post("/classes/join", json={"join_code": cls["join_code"]})
        a = make_assignment(teacher, cls["class_id"], settings)
        res = student.post(f"/assignments/{a['assignment_id']}/submit", json={"answers": answers})
        return teacher, student, a, res

    def test_auto_grading_with_equivalence(self, clients):
        # 2.5 is numerically equivalent to 5/2 — sympy should accept it
        _, _, _, res = self._submit(clients, ["5", "2.5"])
        assert res.status_code == 200
        d = res.get_json()
        assert d["auto_total"] == 5.0
        assert d["max_total"] == 5.0

    def test_wrong_and_blank_answers(self, clients):
        _, _, _, res = self._submit(clients, ["7", ""])
        d = res.get_json()
        assert d["auto_total"] == 0.0
        assert d["answers"][0]["is_correct"] is False
        assert d["answers"][1]["is_correct"] is False

    def test_solutions_shown_by_default(self, clients):
        _, _, _, res = self._submit(clients, ["5", "5/2"])
        assert "solutions" in res.get_json()

    def test_solutions_hidden_when_setting_off(self, clients):
        teacher, student = clients
        cls = make_class(teacher)
        student.post("/classes/join", json={"join_code": cls["join_code"]})
        a = make_assignment(teacher, cls["class_id"],
                            settings={"show_solutions_after_submit": False})
        res = student.post(f"/assignments/{a['assignment_id']}/submit",
                           json={"answers": ["5", "5/2"]})
        d = res.get_json()
        assert "solutions" not in d
        # Still hidden on the results view before grading
        sub = student.get(f"/submissions/{d['submission_id']}").get_json()
        assert "solutions" not in sub

    def test_resubmit_blocked(self, clients):
        teacher, student, a, res = self._submit(clients, ["5", "5/2"])
        res2 = student.post(f"/assignments/{a['assignment_id']}/submit",
                            json={"answers": ["5", "5/2"]})
        assert res2.status_code == 409

    def test_teacher_override_and_student_view(self, clients):
        teacher, student, a, res = self._submit(clients, ["5", "2.4"])
        d = res.get_json()
        assert d["auto_total"] == 2.0

        # Teacher grades: partial credit + comment on question 2
        subs = teacher.get(f"/assignments/{a['assignment_id']}/submissions").get_json()
        sid = subs["submissions"][0]["submission_id"]
        g = teacher.post(f"/submissions/{sid}/grade", json={"overrides": [
            {"question_index": 1, "teacher_score": 1.5, "teacher_comment": "Method fine, slip at the end"},
        ]})
        assert g.status_code == 200
        assert g.get_json()["final_total"] == 3.5

        # Student sees the override, comment, and solutions (graded ⇒ always visible)
        view = student.get(f"/submissions/{sid}").get_json()
        assert view["submission"]["status"] == "graded"
        assert view["submission"]["final_total"] == 3.5
        ans1 = [x for x in view["answers"] if x["question_index"] == 1][0]
        assert ans1["teacher_score"] == 1.5
        assert ans1["teacher_comment"] == "Method fine, slip at the end"
        assert "solutions" in view

    def test_grade_score_out_of_range_rejected(self, clients):
        teacher, student, a, res = self._submit(clients, ["5", "5/2"])
        subs = teacher.get(f"/assignments/{a['assignment_id']}/submissions").get_json()
        sid = subs["submissions"][0]["submission_id"]
        g = teacher.post(f"/submissions/{sid}/grade", json={"overrides": [
            {"question_index": 1, "teacher_score": 99},
        ]})
        assert g.status_code == 400

    def test_cross_teacher_cannot_grade(self, clients):
        teacher, student, a, res = self._submit(clients, ["5", "5/2"])
        sid = res.get_json()["submission_id"]
        other = flask_app.app.test_client()
        other.post("/auth/register", json={"username": "other2", "password": "secret1", "role": "teacher"})
        assert other.post(f"/submissions/{sid}/grade", json={"overrides": []}).status_code == 403
        assert other.get(f"/submissions/{sid}").status_code == 403

    def test_student_cannot_see_others_submission(self, clients):
        teacher, student, a, res = self._submit(clients, ["5", "5/2"])
        sid = res.get_json()["submission_id"]
        other = flask_app.app.test_client()
        other.post("/auth/register", json={"username": "peer", "password": "secret1", "role": "student"})
        assert other.get(f"/submissions/{sid}").status_code == 403
