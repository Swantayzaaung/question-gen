"""
Worked example view modes for generated items.
"""

from __future__ import annotations


def get_worked_example_view(item, mode: str = "full") -> dict:
    """
    Return a view of the worked solution in the requested mode.
    modes: full | fade_last | fade_middle | minimal | independent
    """
    steps = list(item.canonical_solution)

    if mode == "full":
        return {"steps": steps, "final_answer": item.final_answer, "hidden_indices": []}

    elif mode == "fade_last":
        hidden = [len(steps) - 1] if steps else []
        visible = [s if i not in hidden else "???" for i, s in enumerate(steps)]
        return {"steps": visible, "final_answer": "???", "hidden_indices": hidden}

    elif mode == "fade_middle":
        if len(steps) < 3:
            return get_worked_example_view(item, "full")
        mid = len(steps) // 2
        hidden = [mid]
        visible = [s if i not in hidden else "???" for i, s in enumerate(steps)]
        return {"steps": visible, "final_answer": item.final_answer, "hidden_indices": hidden}

    elif mode == "minimal":
        return {"steps": [f"Hint: {steps[0]}"] if steps else [], "final_answer": "???", "hidden_indices": list(range(1, len(steps)))}

    elif mode == "independent":
        return {"steps": [], "final_answer": "???", "hidden_indices": list(range(len(steps)))}

    return get_worked_example_view(item, "full")
