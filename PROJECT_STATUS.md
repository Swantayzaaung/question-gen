# Project Status Report — Math Question Generator & Classroom Platform

*Last updated: 2026-07-06*

## 1. What the project is

An AI-powered practice-question system for **Edexcel International A Level (IAL)
Pure Mathematics (P2)**, aimed at tutoring centers (initially Myanmar). It has
grown from a single-purpose question generator into a small digital-classroom
platform. Two things distinguish it:

1. **Solvability scoring** — a heuristic that predicts whether a generated
   question is clean and well-formed enough to actually use (steps required,
   answer cleanliness, topic scope).
2. **Template-first generation** — deterministic Python templates produce
   verified questions for free, with the LLM reserved for topics/styles that
   don't yet have a template.

## 2. Current state at a glance

| Area | Status |
|---|---|
| Question generation (template + LLM) | Working |
| SymPy answer verification | Working (6 topics) |
| Solvability scoring | Working |
| Web generator UI (KaTeX, difficulty controls) | Working |
| Paper builder + PDF export | Working |
| User accounts (teacher/student) | Working |
| Classroom: classes, enrollment, assignments | Working |
| Auto-grading + teacher override/corrections | Working |
| Mastery tracking (BKT) | Working, lightly used |
| Adaptive recommendations | Built, minimal UI |
| Test suite | 83 passing |
| Codebase | ~5,000 lines Python + 3 HTML pages |

**Data currently ingested:** 6 past papers → 61 questions → 168 parts, spanning
14 topics. 6 of those topics have deterministic templates; 8 rely on the LLM.

## 3. How to run

```bash
cd "math project"
source venv/bin/activate
python3 app.py                 # serves on http://localhost:5001
```

Environment (`.env`, gitignored — copy from `.env.example`):
- `ANTHROPIC_API_KEY` — required for LLM generation (templates work without it)
- `SECRET_KEY` — Flask session signing; set to a long random string
- `FLASK_ENV=development` — enables debug mode

Other commands:
```bash
python3 -m pytest tests/ -q    # run the 83-test suite
python3 src/ingest.py          # rebuild the question bank from PDFs in pastpapers/
```

The `data/` directory (images, parsed JSON, SQLite DB) and `venv/` are
gitignored and rebuilt locally — a fresh clone needs
`pip install -r requirements.txt` then `python3 src/ingest.py`.

## 4. Internal processing structures

### 4.1 Generation pipeline (`src/generator.py`)

```
generate_question(topic, steps, cleanliness, focus)
    │
    ├─ Template exists for topic?
    │     → sample_parameters()      (exact arithmetic, Fraction-based)
    │     → build_question()          → GeneratedItem
    │     → verify_item()             (SymPy: recompute answer, compare)
    │     → LLM rephrase              (Edexcel wording; math is NOT changed)
    │     → quality gate              (8 checks incl. near-duplicate)
    │     → status: verified/approved, source: template/hybrid
    │
    └─ No template (or LLM path)
          → Claude generates full question from past-paper few-shot examples
          → stored with status: needs_review, source: llm
          → teacher can later approve → becomes reusable
```

The template path is free, instant, and deterministically correct. The LLM path
is the R&D path for new topics and gets "crystallized" into templates over time.

### 4.2 Solvability score

Three weighted penalties (`src/annotator.py`):
- **Significant steps** (0.30) — M-marks from the mark scheme = distinct techniques
- **Answer cleanliness** (0.40) — field distance between input and answer number type
- **Adjunct count** (0.30) — extra syllabus topics beyond the head topic

Score → label: HIGH (≥0.75) / MODERATE (≥0.50) / LOW.

### 4.3 Classroom & grading (blueprint architecture)

`app.py` is a thin factory; routes live in `src/blueprints/`:
- `auth.py` — register / login / logout / me (session-based, werkzeug hashing)
- `generation.py` — generate, attempt, item review, mastery, recommendations
- `papers.py` — saved-paper CRUD + printable export
- `classroom.py` — classes, join codes, enrollment, assignments
- `grading.py` — submissions, auto-grade, teacher override, publish

Shared authorization in `src/authz.py` (role decorators + ownership/enrollment
checks). Auto-grading logic in `src/services/grading.py`.

**Grading flow:** student submits → each answer checked with
`sympy_tools.equivalent()` against the canonical answer → full marks if correct,
0 otherwise → misconceptions tagged → teacher reviews, overrides per-answer
scores, adds written comments → publishes → student sees corrected result +
solutions.

**Key design choices:**
- Assignments **snapshot** their questions, so editing a saved paper later can't
  change an already-issued assignment.
- Students never receive canonical answers in the browser before submitting
  (answer keys stripped server-side).
- One submission per student per assignment (no retakes yet).

### 4.4 Data model (SQLite, `src/database.py`)

- **Past-paper bank:** `papers`, `questions`, `parts`
- **Generation:** `generated_items`, `student_attempts`, `skill_mastery`,
  `item_stats`
- **Accounts & classroom:** `users`, `saved_papers`, `classes`, `enrollments`,
  `assignments`, `submissions`, `submission_answers`

### 4.5 Full route list

```
Auth:        /auth/register  /auth/login  /auth/logout  /auth/me
Generate:    /  /generate  /attempt  /topics  /mastery  /recommendations
             /item/<id>  /item/<id>/review
Papers:      /papers (GET/POST)  /papers/<id> (GET/DELETE)  /paper/print
Classroom:   /classroom  /classes (GET/POST)  /classes/join
             /classes/<id>  /classes/<id>/assignments
             /classes/<id>/students/<sid>  /assignment/<id>
             /assignments/<id>  /assignments/<id>/submit
             /assignments/<id>/submissions
Grading:     /submissions/<id>  /submissions/<id>/grade
```

## 5. Most recent changes (commit `cd530c6`)

The digital-classroom overhaul — the largest change to date:
- Restructured `app.py` into five Flask blueprints + authz/services layers
- Added full student accounts and enrollment
- Classes with 6-character join codes
- Assignments (with question snapshotting) built from saved papers
- Auto-grading via the SymPy verifier + misconception tagging
- Teacher override of scores and written corrections, then publish
- Two new pages: `/classroom` (role-aware) and `/assignment/<id>`
- 20 new tests (lifecycle, authorization boundaries, snapshot immutability)
- Verified end-to-end in a real browser (teacher and student journeys)

Prior recent commit (`e627b37`): paper builder, PDF export, SymPy install, and
the template→verify→rephrase pipeline wiring.

## 6. Known gaps & limitations

- **Auto-grading is all-or-nothing per question** — no method/partial marks
  automatically; that's exactly what teacher override is for, but it means
  multi-part questions with per-part marks aren't auto-split.
- **8 of 14 topics have no template** — they always use the (paid, unverified)
  LLM path: coordinate geometry, polynomials, trig identities, trig equations,
  proof, exponential functions, and two sequences variants.
- **One syllabus, one unit** — only Edexcel IAL P2 is ingested (6 papers).
- **Mastery/recommendations under-surfaced** — the BKT engine works but has
  minimal UI; recommendations aren't shown to students yet.
- **No deployment config** — dev-server only; no gunicorn/Procfile, SQLite not
  suited to concurrent multi-user production.
- **No retakes, no due-date enforcement by default** (advisory unless
  `allow_late: false`).
- **`worked_examples.py` is a stub.**

## 7. Roadmap — improving & expanding scope

### 7.1 Expanding to more papers & syllabuses (the big lever)

The ingestion pipeline (`pdf_to_images → parse_question_paper /
parse_markscheme → annotator → database`) is already syllabus-agnostic in
principle, but a few things are hardcoded to Edexcel IAL P2:

1. **Generalize the paper identifier & metadata** — `ingest.py` parses filenames
   with an Edexcel-specific regex and assumes unit P2. Needs a syllabus/unit
   field carried through `papers` (partially there) and surfaced in the UI as a
   filter.
2. **Topic taxonomy per syllabus** — `skills.py` is a hand-built Edexcel P2 skill
   graph. Each new syllabus (P1/P3/P4, Statistics, Mechanics; or CIE, AQA) needs
   its own topic list and skill graph. Consider a data-driven taxonomy
   (JSON/DB) rather than Python code.
3. **Templates are syllabus-independent maths** — a differentiation template
   works regardless of exam board, but question *phrasing* and *mark
   conventions* differ. Templates may need per-board wording variants.
4. **UI: syllabus/unit selector** — the generator and classroom currently assume
   one context; add a top-level picker once multiple are ingested.

**Concrete next step:** ingest more P2 papers first (cheapest — same taxonomy),
then add P1 as the first cross-unit test of the pipeline's generality.

### 7.2 Filling template coverage

Write deterministic templates for the 8 LLM-only topics. Each converts a topic
from "paid + unverified" to "free + instant + verified." The LLM can draft the
template code (`sample_parameters` / `solve` / `build_question`) for human
review. Priority: coordinate geometry, trig equations, polynomials (highest
question volume in the bank).

### 7.3 Grading depth

- Per-part auto-grading (split marks across sub-parts a/b/c)
- Partial-credit heuristics (e.g. correct method, wrong final value)
- Rubric support for proof/"show that" questions the verifier can't check

### 7.4 Platform hardening (needed before real deployment)

- Production server (gunicorn) + `Procfile`/Dockerfile
- Migrate SQLite → Postgres for concurrent users
- Rate limiting on generation (cost control), CSRF protection
- Password reset, email/username uniqueness policy, session hardening

### 7.5 Pedagogy features (build on existing engine)

- Surface mastery + "what to practice next" to students
- Finish `worked_examples.py`
- Per-class analytics for teachers (question difficulty from real attempt data
  via `item_stats`)

### 7.6 Data & research

- The solvability metric is currently heuristic; with real student attempt data
  (`student_attempts`, `item_stats`) it could be calibrated empirically — the
  original research angle.

## 8. Test coverage

83 tests across: `test_api.py` (routes), `test_templates.py` (6 templates),
`test_math_verifier.py` (SymPy verification), `test_scheduler.py` (mastery/
recommendations), `test_classroom.py` (full classroom lifecycle, authorization
boundaries, snapshot immutability, auto-grade + override).
