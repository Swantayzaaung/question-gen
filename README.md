# Adaptive Math Practice Engine
### Edexcel IAL Pure Mathematics P2

An adaptive practice system for Edexcel IAL P2 mathematics.
The backend is **deterministic first** — LLMs draft wording and classify, but never certify mathematical correctness.

---

## What this app does

- Generates Edexcel-style P2 exam questions from parametric templates
- Deterministically verifies every generated answer using SymPy
- Accepts student answers and marks them correct/incorrect
- Updates per-skill mastery estimates using Bayesian Knowledge Tracing (BKT-lite)
- Recommends next practice items using spacing and interleaving
- Falls back to LLM-only generation for topics without templates, clearly marking those items as unverified

---

## Architecture

```
src/
  app.py                   Flask routes (/ generate /attempt /mastery /recommendations /item/:id)
  schemas.py               Pydantic data models (GeneratedItem, LearnerAttempt, MasteryState, …)
  skills.py                P2 skill graph with prerequisites and misconceptions
  generator.py             Orchestrates template → verify → LLM rephrase → quality gate → store

  templates/               Parametric item generators (deterministic math, no LLM for numbers)
    arithmetic_series.py
    geometric_series.py
    differentiation.py
    integration.py
    logarithms.py
    binomial_expansion.py

  verification/            SymPy-based correctness checking
    math_verifier.py       verify_item() dispatches by topic
    sympy_tools.py         normalize_expr, equivalent, is_integer_answer, …
    similarity.py          Jaccard near-duplicate detection
    validators.py          Input validation for API routes

  adaptation/              Learner modelling
    mastery.py             BKT-lite update and persistence
    scheduler.py           Spaced, interleaved recommendation

  pedagogy/
    worked_examples.py     Full/fade/minimal solution views
    misconception_tags.py  Answer-pattern heuristic misconception detection

  quality/
    item_quality.py        Multi-gate quality evaluation

  database.py              SQLite: papers, questions, parts, generated_items, attempts, mastery

tests/
  test_templates.py
  test_math_verifier.py
  test_scheduler.py
  test_api.py
```

---

## Why LLM is not the source of truth

An LLM can hallucinate numbers, introduce wrong algebra, and confidently report incorrect answers.
This system uses LLMs **only** for:
- Rephrasing template question text in Edexcel style
- Classifying topics for questions without templates
- Generating fallback questions when no template exists (marked `needs_review`)

The **source of truth** for mathematical correctness is SymPy. Every template-generated item is
independently solved and verified before it is labelled `verified` or `approved`.

If SymPy cannot verify an item, its status is `needs_review`, not `approved`.
The frontend shows a warning for unverified items.

---

## How generation works

```
generate_question(topic, steps, cleanliness, focus)
  │
  ├─ Template exists?
  │    ├─ sample_parameters()        ← deterministic sampling
  │    ├─ build_question(params)     ← canonical item with known answer
  │    ├─ verify_item(item)          ← SymPy recomputes the answer
  │    ├─ LLM rephrase (optional)    ← only changes wording, not numbers
  │    ├─ evaluate_quality(item)     ← quality gates
  │    └─ store + return (status: approved/verified)
  │
  └─ No template
       ├─ LLM generates everything
       └─ return (status: needs_review — NEVER approved automatically)
```

---

## How verification works

`verify_item(item)` dispatches to topic verifiers in `verification/math_verifier.py`.

Each verifier:
1. Reads the `item.parameters` dict (not the LLM-reported answer)
2. Recomputes the correct answer using SymPy
3. Compares `item.final_answer` to the computed answer with `equivalent()`
4. Returns a `VerifierResult` with `is_correct`, `checks`, `errors`, and `warnings`

`equivalent(a, b)` uses SymPy symbolic simplification + numeric fallback.

---

## How adaptive practice works

**Mastery model** — BKT-lite (Bayesian Knowledge Tracing, simplified):

| Parameter | Value | Meaning |
|-----------|-------|---------|
| P_INIT    | 0.25  | Prior mastery |
| P_LEARN   | 0.10  | P(learn after correct attempt) |
| P_GUESS   | 0.20  | P(correct \| unmastered) |
| P_SLIP    | 0.10  | P(incorrect \| mastered) |

Mastery updates after each attempt. Hints penalise the evidential weight of a correct answer.

> **Limitation**: these parameters are not calibrated on real student data.
> They are reasonable priors. Do not report BKT estimates as psychometric ground truth.
> Full IRT (3-parameter logistic model) should only be fitted once thousands of attempts exist.

**Scheduler** (`adaptation/scheduler.py`) selects items by:
- Prioritising weak skills (low mastery_probability)
- Including due-for-review skills (next_due ≤ now)
- Interleaving topics (no same topic twice in a row if avoidable)
- Avoiding recently attempted items

**Spacing intervals** after correct attempt:
| Mastery | Next due |
|---------|----------|
| Failed  | 10 min   |
| < 0.4   | 1 day    |
| 0.4–0.7 | 3 days   |
| 0.7–0.85| 7 days   |
| > 0.85  | 14 days  |

---

## How to add a new topic template

1. Create `src/templates/my_topic.py` extending `ItemTemplate` from `templates/base.py`.
2. Implement `sample_parameters()`, `solve()`, `build_question()`, `validate_params()`.
3. Register in `src/templates/__init__.py`:
   ```python
   from .my_topic import MyTopicTemplate
   TEMPLATE_MAP["my_topic"] = MyTopicTemplate
   ```
4. Add skills to `src/skills.py`.
5. Add a topic verifier in `src/verification/math_verifier.py`.
6. Write tests in `tests/test_templates.py`.

---

## How to ingest new past papers

```bash
python3 src/ingest.py --paper pastpapers/paper.pdf --ms pastpapers/ms.pdf
```

Requires `ANTHROPIC_API_KEY` in `.env`.

---

## How to run tests

```bash
python3 -m pip install pytest sympy pydantic flask anthropic python-dotenv
python3 -m pytest tests/ -q
```

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate` | Generate a question |
| POST | `/attempt` | Submit a student answer |
| GET  | `/mastery?user_id=X` | Get skill mastery table |
| GET  | `/recommendations?user_id=X&n=5` | Get recommended next items |
| GET  | `/item/:item_id` | Get an approved item |
| GET  | `/topics` | List available topics |

### POST /generate
```json
{
  "topic": "arithmetic_series",
  "steps": 2,
  "cleanliness": "clean",
  "focus": "single"
}
```

### POST /attempt
```json
{
  "user_id": "default",
  "item_id": "tmpl_arithmetic_series_abc12345",
  "submitted_answer": "120",
  "time_seconds": 45,
  "hints_used": 0
}
```

---

## Known limitations

- **Heuristic solvability score** is a formula-based proxy, not a psychometric difficulty measure.
  Empirical difficulty (p-correct) requires real student response data.
- **BKT mastery** parameters are not calibrated — treat as rough estimates.
- **Misconception detection** is heuristic: without student working shown, it can only catch
  obvious patterns (sign errors, negative log arguments).
- **LLM-generated items** (fallback for topics without templates) are `needs_review` and
  may contain mathematical errors. Do not serve them as approved items without human review.
- **Near-duplicate detection** uses Jaccard bigram similarity — it misses paraphrases with
  different phrasing but same structure.
- The differentiation template only generates cubics. Extend it for other polynomial degrees.
