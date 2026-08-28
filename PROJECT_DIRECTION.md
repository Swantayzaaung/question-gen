# PROJECT DIRECTION — Updated August 2026

*Read this alongside PROJECT_STATUS.md (last updated 2026-07-06). Where the two
conflict, this document wins — it records a deliberate change of direction made
after that status report was written.*

---

## 1. What changed

The project was previously framed as a **product**: an AI practice-question
platform for tutoring centers, with a roadmap oriented toward more syllabuses,
more features, deployment hardening, and eventually users.

It is now framed as a **research instrument**, with the platform as the
apparatus rather than the deliverable.

**The research question:**

> Can the difficulty of an exam question be predicted from structural properties
> of the question and its mark scheme, rather than from student response data
> collected after the fact?

The existing `solvability_score` in `src/annotator.py` is the prototype answer to
that question — but its three weights (0.30 significant steps / 0.40 answer
cleanliness / 0.30 adjunct count) are currently **hand-chosen, not empirically
derived**. Replacing those guessed weights with coefficients fitted against real
difficulty data is the core of the project now.

This was already identified as the "original research angle" in
PROJECT_STATUS.md §7.6. It has been promoted from last item on the roadmap to
the main line of work.

## 2. Why the pivot

- **No users, and no plan to get them this year.** Distribution is a full-time
  effort and the author is a sophomore in an active recruiting cycle. Building
  product features for zero users is not a good use of the remaining time.
- **The calibration is the defensible part.** An AI study tool is a weekend
  clone. A difficulty model validated against a decade of examiner data is not.
  If the project ever becomes a product, this is the moat.
- **It suits an academic path.** The intended next step is an independent study
  or UTRA with a Brown faculty advisor, with a workshop paper (BEA / AIED / EDM)
  as a possible outcome. That path wants a research question, not a feature list.
- **Related literature exists.** The field is *question difficulty estimation*
  (QDE) in NLP, and *item response theory* (IRT) in psychometrics. Most QDE work
  predicts difficulty from question text via embeddings. This project's angle is
  different and worth stating explicitly: **interpretable, pedagogically
  meaningful features derived from the mark scheme's solution structure**, not
  black-box text embeddings. Interpretability is the point — the features are
  meant to be causal levers a teacher or generator can act on, not just
  predictors.

## 3. Scope decisions (settled — do not relitigate)

| Question | Decision |
|---|---|
| Syllabus | **Edexcel IAL P2 only.** Do not add P1/P3/P4 or other boards yet. Generality before validity is backwards. |
| Users / deployment | **None this year.** No gunicorn, no Postgres, no CSRF, no password reset. |
| Classroom platform | **Frozen.** It works; it is done. No retakes, no due-date enforcement, no per-part grading. |
| Missing templates | **Low priority.** LLM-path questions are fine as *data points* even if they're unverified as *product*. |
| Product vs research | **Research first.** Product decision deferred to spring/summer 2027 at the earliest. |

## 4. What the work is now

### Phase 1 — Corpus (in progress)

Currently ingested: **6 papers → 61 questions → 168 parts, 14 topics.** Far too
thin to fit anything.

- [ ] Ingest to **25–30 P2 papers** (~250–300 questions). Edexcel IAL runs
      Jan/June/Oct sessions, so this is roughly 8–10 years of coverage.
- [ ] **Download the examiner report alongside every paper.** Consistent naming
      (`2019_jun_P2_er.pdf`). These are the ground-truth source and must not be
      collected in a second pass later.
- [x] Add a **`spec_version`** field to the `papers` table now (Edexcel IAL spec
      changed ~2018-19; old- and new-spec papers may not pool cleanly, but that
      is only checkable if the papers are tagged). *Done: `papers` now carries
      `spec_version` + `er_file`; `ingest.py` derives spec from year (2019+ →
      `IAL_2018`) and links each ER as a first-class file.*
- [ ] Expect the parser to break on older papers — formatting drifts across
      years. Ingest newest-to-oldest and fix as it breaks. (This robustness work
      is a legitimate README line: "handles 10 years of format drift.")
- [ ] **Spot-check ~5 questions per paper** against parsed output (text intact,
      marks per part correct, position number right). Silent parse errors are how
      this kind of dataset rots.

### Phase 2 — Features (mostly already built)

Good news: `src/annotator.py` already computes the three core features
(significant steps from M-marks, answer cleanliness, adjunct count). What's
needed is to expose them as a clean feature table and add the free ones:

- [ ] Emit a per-question/per-part **feature table** (CSV or DB view) with:
      significant steps, answer-form divergence, topic span, **marks allocated**,
      **question position in paper**, **word count**, `spec_version`, year.
- [ ] Hand-check ~20 questions against tutoring intuition. **Write down every
      disagreement** — where the metric and the intuition diverge is the most
      interesting material in the project, and the best thing to show a professor.

### Phase 3 — Ground truth + modelling (the actual research)

- [ ] Parse **examiner reports** for difficulty signal — which questions
      candidates handled poorly. Even a manual pass labelling questions as
      poorly-answered / mixed / well-answered is usable.
- [ ] Fallback proxy where reports are thin: **marks per part** (the board's own
      crude difficulty assignment).
- [ ] Fit an **interpretable model** (linear/logistic regression — interpretability
      is a feature here, not a limitation). The deliverable is the **coefficient
      analysis**: which features actually carry signal.
- [ ] Test the **position effect**: does question position predict poor
      performance independently of structural features? (Cheap version of the
      perceived-difficulty question, no human subjects needed.)
- [ ] **Write this part manually**, not with heavy AI assistance. It's a few
      hundred lines of pandas/scikit-learn, it's the intellectually original part,
      and doing it by hand closes a real capability gap.

### Phase 4 — Making it legible

- [ ] Rewrite `PROJECT_STATUS.md` into a **public, research-framed README**:
      question → method → early findings → future work. Add a demo GIF.
      *(Blocking: the repo is not public yet, and resume bullets point at it.)*
- [ ] Email 2–3 Brown professors (NLP / CS education / learning sciences) with
      the project brief. Ask about independent study or UTRA for spring.

### Phase 5 — Later (do not start before spring 2027)

- Wire validated metrics back into the generator as real difficulty controls;
  evaluate whether "generate hard" actually produces hard questions.
- Assess workshop-paper viability with an advisor.
- Revisit the product question, if still wanted.

## 5. Constraints on the work

- **Time budget: evenings and weekends only.** Recruiting (LeetCode, applications,
  interviews) and the UTRA come first through at least November.
- Paper ingestion is deliberately **low-cognitive-load** work — good for tired
  evenings. Modelling work needs a clear head; save it for weekends.
- In the fall semester this project goes to **near-dormant**: README + professor
  emails only.

## 6. One-sentence pitch (for professors, interviews, README)

> Generation is easy and past papers are free — that's the point. The unsolved
> problem is knowing how hard a question is without giving it to a thousand
> students first. This project builds the measurement layer, validated against a
> decade of examiner data.

---

## Immediate next steps

1. ~~Verify how many examiner reports are already downloaded and where they live.~~
   **Done: 18 P2 papers, 16 with ERs (Jun 2021 & MJ-R 2024 have none published).**
2. ~~Add `spec_version` to the `papers` schema.~~ **Done, plus `er_file` and a
   generalized ingester for the `P2/<year>/Maths P2 <session> <year> <QP|MS|ER>`
   layout.**
3. ~~Resume paper ingestion toward the 25–30 target.~~ **Superseded: corpus
   locked at the 18 new-spec P2 papers (the full available new-spec universe).
   Revisit only if the model is signal-starved; old-spec C12 would enter as a
   separate spec-tagged pool, never pooled with P2.**
4. **Next:** re-ingest the 18 papers into a clean DB (API-cost step), then emit
   the feature table and eyeball it.
