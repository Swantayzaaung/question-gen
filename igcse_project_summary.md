# IGCSE Math Question Generator — Project Summary

## One-line pitch
An AI tool that generates syllabus-aligned IGCSE Math questions with a "solvability" score that predicts whether a question is clean and well-formed enough to actually use in an exam or worksheet.

## The problem
IGCSE Math tutors and tutoring centers spend significant time manually preparing worksheets and practice questions. Existing topical question banks (Best Exam Help, Papa Cambridge, Physics and Math Tutor) are manually compiled and finite. There is no tool that generates unlimited new questions calibrated to a specific syllabus topic and difficulty level, let alone one that filters out badly-formed questions automatically.

## The differentiator — solvability scoring
The novel feature. Most AI math question generators just prompt a model and hope the output is usable. This tool evaluates whether a generated question is actually clean:
- Does the answer resolve to a clean number or simple expression?
- Are the intermediate steps reasonable in length and complexity?
- Is the difficulty level appropriate for the target grade?
- A question resolving to 2 via neat steps = high solvability. A question resolving to 533/71 with messy logarithms = low solvability, regenerate.

Implementation approach: SymPy (symbolic math engine in Python) to evaluate answer cleanliness, heuristics on top for step complexity, optionally a small ML scoring layer trained on human feedback later.

## Target users
**Primary (monetization target):** Tutoring centers in Myanmar — there are many, they're businesses, they already charge parents, they can absorb a tool cost. Time savings on worksheet prep is the value proposition.

**Secondary:** Individual IGCSE tutors, self-studying students.

## Core features (in priority order)
1. **Topic-based question generation** — input a syllabus topic + difficulty level, get a generated question + worked solution
2. **Solvability scoring** — automatic quality filter on generated questions
3. **Difficulty mapping** — classify questions by topic and difficulty using past paper data as reference
4. **Worksheet export** — bundle generated questions into a downloadable worksheet (freemium upsell)

## Data sources
Past papers and mark schemes scraped from publicly accessible aggregator sites (Best Exam Help, Papa Cambridge, PMT). Used as few-shot examples for generation and as training signal for difficulty calibration. Not redistributed directly.

## Tech stack (suggested)
- **Backend:** Python + Flask
- **Math engine:** SymPy for symbolic answer evaluation
- **AI layer:** Claude API or OpenAI for question generation, with past paper examples as few-shot context
- **Frontend:** React or simple Flask templates for hackathon speed
- **Database:** SQLite for storing syllabus structure, generated questions, solvability scores

## Hackathon MVP scope
Single demo-able loop:
1. User selects a topic (e.g. quadratic equations) and difficulty
2. System generates a question + worked solution
3. System displays a solvability score with brief explanation
4. User can regenerate if score is low

One topic, one difficulty slider, one output. Demonstrable in 2 minutes to a judge.

## Longer-term vision
- Expand across IGCSE Math syllabus topics
- Add other IGCSE subjects (Physics, CS)
- B2B licensing to tutoring centers at flat monthly rate
- Research paper on solvability metric as a formal mathematical construct

## Why this builder
- Former IGCSE tutor (Myanmar + Thailand, 2023-2024) — knows the student pain points from both sides
- Built MarkerAI: AI-assisted past paper grading using OCR + NLP + Django — directly adjacent technical foundation
- Personal network in Myanmar tutoring community for early user acquisition
- APMA-CS student at Brown — credibility for the research angle on solvability
