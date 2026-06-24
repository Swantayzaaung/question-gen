"""
Bayesian Knowledge Tracing (BKT-lite) mastery model.
This is a lightweight mastery estimate — not full IRT.
Do not use as psychometric ground truth without student response data calibration.
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

# BKT default parameters
P_INIT = 0.25     # prior mastery
P_LEARN = 0.10    # transition: unmastered → mastered after correct
P_GUESS = 0.20    # P(correct | unmastered)
P_SLIP = 0.10     # P(incorrect | mastered)


def bkt_update(p_mastery: float, is_correct: bool, hints_used: int = 0) -> float:
    """
    Update mastery probability using BKT-lite.
    hints_used reduces the evidential weight of a correct answer.
    """
    # Adjust effective correctness for hints
    hint_penalty = min(0.5, hints_used * 0.15)
    effective_p_slip = P_SLIP + hint_penalty
    effective_p_guess = P_GUESS + hint_penalty

    if is_correct:
        # P(mastered | correct) via Bayes
        p_obs_given_mastered = 1 - effective_p_slip
        p_obs_given_unmastered = effective_p_guess
    else:
        p_obs_given_mastered = effective_p_slip
        p_obs_given_unmastered = 1 - effective_p_guess

    p_obs = p_mastery * p_obs_given_mastered + (1 - p_mastery) * p_obs_given_unmastered
    if p_obs < 1e-10:
        return p_mastery

    p_posterior = (p_mastery * p_obs_given_mastered) / p_obs

    # Apply learning transition (only on correct)
    if is_correct:
        p_posterior = p_posterior + (1 - p_posterior) * P_LEARN

    return max(0.0, min(1.0, p_posterior))


def _next_due(mastery: float, is_correct: bool) -> str:
    """Compute next_due timestamp based on mastery and correctness."""
    now = datetime.now()
    if not is_correct:
        delta = timedelta(minutes=10)
    elif mastery < 0.4:
        delta = timedelta(days=1)
    elif mastery < 0.7:
        delta = timedelta(days=3)
    elif mastery < 0.85:
        delta = timedelta(days=7)
    else:
        delta = timedelta(days=14)
    return (now + delta).isoformat()


def update_mastery(user_id: str, skill_id: str, is_correct: bool,
                   hints_used: int = 0, db_path: str = None) -> "MasteryState":
    """Update skill mastery after an attempt and persist to DB."""
    from database import get_connection
    from schemas import MasteryState

    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM skill_mastery WHERE user_id=? AND skill_id=?",
        (user_id, skill_id)
    ).fetchone()

    if row:
        current = dict(row)
        p = float(current["mastery_probability"])
        correct_streak = int(current["correct_streak"])
        incorrect_streak = int(current["incorrect_streak"])
    else:
        p = P_INIT
        correct_streak = 0
        incorrect_streak = 0

    p_new = bkt_update(p, is_correct, hints_used)

    if is_correct:
        correct_streak += 1
        incorrect_streak = 0
    else:
        incorrect_streak += 1
        correct_streak = 0

    next_due = _next_due(p_new, is_correct)
    now = datetime.now().isoformat()

    conn.execute("""
        INSERT OR REPLACE INTO skill_mastery
            (user_id, skill_id, mastery_probability, last_practiced, next_due,
             correct_streak, incorrect_streak, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, skill_id, p_new, now, next_due, correct_streak, incorrect_streak, now))
    conn.commit()
    conn.close()

    return MasteryState(
        user_id=user_id,
        skill_id=skill_id,
        mastery_probability=p_new,
        last_practiced=now,
        next_due=next_due,
        correct_streak=correct_streak,
        incorrect_streak=incorrect_streak,
    )


def get_mastery(user_id: str, skill_id: str, db_path: str = None) -> "MasteryState":
    from database import get_connection
    from schemas import MasteryState
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM skill_mastery WHERE user_id=? AND skill_id=?",
        (user_id, skill_id)
    ).fetchone()
    conn.close()
    if row:
        d = dict(row)
        return MasteryState(**{k: d[k] for k in MasteryState.model_fields if k in d})
    return MasteryState(user_id=user_id, skill_id=skill_id)


def get_all_mastery(user_id: str, db_path: str = None) -> list["MasteryState"]:
    from database import get_connection
    from schemas import MasteryState
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM skill_mastery WHERE user_id=? ORDER BY mastery_probability ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        result.append(MasteryState(**{k: d[k] for k in MasteryState.model_fields if k in d}))
    return result
