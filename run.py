"""
Main entry point. Run this to parse a past paper pair and see solvability signals.

Usage:
    python run.py                    # uses the included Edexcel P2 Jan 2025 sample
    python run.py --paper X --ms Y   # use your own PDF paths
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pdf_to_images import pdf_to_images
from parse_markscheme import parse_markscheme
from parse_question_paper import parse_question_paper
from annotator import merge, solvability_label


BASE = Path(__file__).parent
DEFAULT_PAPER = BASE / "pastpapers" / "Edexcel International A Level (IAL) Maths P2 January 2025 Paper.pdf"
DEFAULT_MS    = BASE / "pastpapers" / "Edexcel International A Level (IAL) Maths P2 January 2025 MS.pdf"

SOLVABILITY_ICON = {"HIGH": "✓", "MODERATE": "~", "LOW": "✗"}
ANSWER_TYPE_NOTE = {
    "integer":     "whole number",
    "rational":    "fraction / decimal",
    "irrational":  "surd / irrational",
    "expression":  "algebraic expression",
    "coordinates": "coordinate pair",
    "proof":       "proof (no numerical answer)",
}


def divider(char="─", width=60):
    print(char * width)


def section(title):
    divider("━")
    print(f"  {title}")
    divider("━")


def run(paper_pdf: str, ms_pdf: str, skip_parse: bool = False):
    paper_id = Path(paper_pdf).stem[:30]

    section(f"IGCSE / A-Level Math Parser")
    print(f"  Paper:       {Path(paper_pdf).name}")
    print(f"  Mark scheme: {Path(ms_pdf).name}")
    print()

    # ── Step 1: PDF → images ───────────────────────────────────────────────
    img_dir_ms    = BASE / "data" / "images" / "markscheme"
    img_dir_paper = BASE / "data" / "images" / "paper"
    ms_json       = BASE / "data" / "parsed" / "markscheme_WMA12_2501.json"
    paper_json    = BASE / "data" / "parsed" / "paper_WMA12_2501.json"
    merged_json   = BASE / "data" / "parsed" / "annotated_WMA12_2501.json"

    if skip_parse and ms_json.exists() and paper_json.exists():
        print("  Skipping parse (cached results found). Use --reparse to force.\n")
    else:
        print("[1/4] Converting PDFs to page images...")
        print("      (each page becomes a PNG so Claude can read the math notation)")
        ms_images    = pdf_to_images(str(ms_pdf),    str(img_dir_ms))
        paper_images = pdf_to_images(str(paper_pdf), str(img_dir_paper))
        print(f"      Mark scheme: {len(ms_images)} pages")
        print(f"      Question paper: {len(paper_images)} pages\n")

        # ── Step 2: Parse mark scheme ──────────────────────────────────────
        print("[2/4] Parsing mark scheme with Claude vision...")
        print("      Extracting: M1/dM1/A1/B1 mark counts, worked steps, final answers")
        print("      (M marks = significant steps — this is our core solvability signal)\n")
        parse_markscheme(ms_images, structured=True, output_path=str(ms_json))

        # ── Step 3: Parse question paper ───────────────────────────────────
        print("\n[3/4] Parsing question paper with Claude vision...")
        print("      Extracting: question text, mark totals, topics, given values\n")
        parse_question_paper(paper_images, output_path=str(paper_json))

    # ── Step 4: Merge + compute solvability ───────────────────────────────
    print("\n[4/4] Merging and computing solvability signals...")
    print("      Combining mark scheme + question paper data")
    print("      Computing: significant steps, answer cleanliness, adjunct count, score\n")
    records = merge(str(paper_json), str(ms_json), output_path=str(merged_json))
    print(f"      Saved to {merged_json}\n")

    # ── Results display ────────────────────────────────────────────────────
    section("RESULTS")
    print()

    for q in records:
        qnum         = q["question_number"]
        topic_head   = q.get("topic_head") or "unknown"
        topics       = q.get("topic_signals", [])
        adjuncts     = q.get("adjunct_count", 0)
        given        = q.get("given_values", [])
        given_types  = q.get("given_value_types", [])

        topic_display = topic_head.replace("_", " ").title()
        extra_topics  = [t.replace("_", " ") for t in topics[1:]] if len(topics) > 1 else []

        print(f"Q{qnum}  {topic_display}")
        divider("─", 50)

        if given:
            print(f"  Given values : {', '.join(given)} ({', '.join(given_types)})")
        if extra_topics:
            print(f"  Also uses    : {', '.join(extra_topics)}  ← {adjuncts} adjunct(s)")
        print()

        for part in q["parts"]:
            label    = part.get("part", "?")
            marks    = part.get("marks", "?")
            steps    = part.get("significant_steps", 0)
            answer   = part.get("final_answer", "?")
            atype    = part.get("answer_type", "?")
            fdist    = part.get("field_distance", "?")
            score    = part.get("solvability_score", 0)
            solv     = part.get("solvability", "?")
            icon     = SOLVABILITY_ICON.get(solv, "?")
            atype_note = ANSWER_TYPE_NOTE.get(atype, atype)
            qtext    = part.get("question_text") or ""

            print(f"  Part {label}  ({marks} marks)  {icon} {solv}  [score: {score}]")
            if qtext:
                print(f"    Task    : {qtext[:80]}")
            print(f"    Answer  : {answer}  [{atype_note}]")
            print(f"    Steps   : {steps} significant step(s)")
            print(f"    Clean?  : field distance = {fdist}  (0=clean, 1=one step away, 2+=messy)")

            worked = part.get("worked_steps", [])
            if worked:
                for i, s in enumerate(worked, 1):
                    print(f"    Step {i}  : {s[:90]}")
            print()

        print()

    # ── Summary table ──────────────────────────────────────────────────────
    section("SOLVABILITY SUMMARY")
    print()
    print(f"  {'Q':<4} {'Topic':<30} {'Parts':<8} {'Avg Score':<12} {'Verdict'}")
    divider("─", 60)

    for q in records:
        qnum  = q["question_number"]
        topic = (q.get("topic_head") or "unknown").replace("_", " ")[:28]
        parts = q["parts"]
        if not parts:
            continue
        scores = [p.get("solvability_score", 0) for p in parts]
        avg    = round(sum(scores) / len(scores), 3)
        label  = solvability_label(avg)
        icon   = SOLVABILITY_ICON[label]

        part_str = " ".join(
            f"{p['part']}:{p.get('solvability_score','?')}" for p in parts
        )
        print(f"  Q{qnum:<3} {topic:<30} {avg:<12} {icon} {label}")
        print(f"       {part_str}")
        print()

    divider("━")
    print(f"  Full annotated data → {merged_json}")
    divider("━")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse a math past paper pair and compute solvability signals.")
    parser.add_argument("--paper", default=str(DEFAULT_PAPER), help="Path to question paper PDF")
    parser.add_argument("--ms",    default=str(DEFAULT_MS),    help="Path to mark scheme PDF")
    parser.add_argument("--reparse", action="store_true",      help="Re-run Claude parsing even if cached results exist")
    args = parser.parse_args()

    run(args.paper, args.ms, skip_parse=not args.reparse)
