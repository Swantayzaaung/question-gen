"""
Adaptive item scheduler with spacing and interleaving.
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


def recommend_next_items(user_id: str, n: int = 5, current_topic: str = None,
                         db_path: str = None) -> list[dict]:
    """
    Recommend next items using:
    - weak skills (low mastery)
    - due-for-review skills
    - interleaving (different topics)
    - avoid same-skill repetition
    """
    from database import get_connection
    from adaptation.mastery import get_all_mastery, P_INIT
    from skills import SKILLS, get_skills_by_topic

    mastery_states = get_all_mastery(user_id, db_path)
    mastery_map = {m.skill_id: m for m in mastery_states}
    now = datetime.now()

    # Collect all skills with mastery info
    skill_entries = []
    for sid, skill in SKILLS.items():
        m = mastery_map.get(sid)
        p = m.mastery_probability if m else P_INIT
        next_due_str = m.next_due if m else None
        is_due = True
        if next_due_str:
            try:
                nd = datetime.fromisoformat(next_due_str)
                is_due = nd <= now
            except Exception:
                pass

        skill_entries.append({
            "skill_id": sid,
            "topic": skill.topic,
            "display_name": skill.display_name,
            "mastery": p,
            "is_due": is_due,
            "next_due": next_due_str,
        })

    # Sort: weak + due first
    def priority(e):
        base = -e["mastery"]  # lower mastery = higher priority
        due_bonus = -0.3 if e["is_due"] else 0
        return base + due_bonus

    skill_entries.sort(key=priority)

    # Select with interleaving: at most 2 from same topic in a row
    selected = []
    topic_counts: dict[str, int] = {}
    used_topics: list[str] = []

    for entry in skill_entries:
        if len(selected) >= n:
            break
        t = entry["topic"]
        if topic_counts.get(t, 0) >= 2:
            continue
        # Interleave: don't repeat same topic consecutively if possible
        if used_topics and used_topics[-1] == t and len(skill_entries) > 3:
            continue
        selected.append(entry)
        topic_counts[t] = topic_counts.get(t, 0) + 1
        used_topics.append(t)

    # If we don't have n, relax constraints
    if len(selected) < n:
        for entry in skill_entries:
            if entry not in selected:
                selected.append(entry)
            if len(selected) >= n:
                break

    # Look up approved items for recommended skills, or suggest generation
    conn = get_connection(db_path)
    recommendations = []
    for entry in selected[:n]:
        # Find an approved item for this skill the user hasn't seen recently
        row = conn.execute("""
            SELECT gi.item_id, gi.topic, gi.question_text, gi.marks, gi.significant_steps
            FROM generated_items gi
            WHERE gi.primary_skill = ? AND gi.status = 'approved'
              AND gi.item_id NOT IN (
                SELECT item_id FROM student_attempts WHERE user_id = ? ORDER BY timestamp DESC LIMIT 3
              )
            ORDER BY RANDOM()
            LIMIT 1
        """, (entry["skill_id"], user_id)).fetchone()

        if row:
            recommendations.append({
                "type": "existing_item",
                "item_id": row["item_id"],
                "topic": row["topic"],
                "skill_id": entry["skill_id"],
                "display_name": entry["display_name"],
                "mastery": entry["mastery"],
                "is_due": entry["is_due"],
            })
        else:
            recommendations.append({
                "type": "generate",
                "topic": entry["topic"],
                "skill_id": entry["skill_id"],
                "display_name": entry["display_name"],
                "mastery": entry["mastery"],
                "suggested_steps": 2 if entry["mastery"] < 0.5 else 3,
                "is_due": entry["is_due"],
            })

    conn.close()
    return recommendations
