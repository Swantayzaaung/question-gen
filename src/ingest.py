"""
Batch ingest pipeline. Recursively scans a folder tree of past papers, parses
any not yet in the database, and stores results in the SQLite question bank.

Layout (current):
    pastpapers/<unit>/<year>/Maths <unit> <session> <year> <QP|MS|ER>.pdf
    e.g. pastpapers/P2/2019/Maths P2 MJ 2019 QP.pdf

Each question paper (QP) is matched to its mark scheme (MS) and, when present,
its examiner report (ER) by swapping the trailing token. Session codes:
    Jan = January, Jun / MJ = May/June, "MJ R" = May/June (Regional),
    ON = October/November.
spec_version tags the Edexcel IAL specification: papers from 2019 onward are the
2018 spec ("IAL_2018", i.e. the P1/P2/P3/P4 units); older papers ("IAL_2008",
the C12/C34 modular structure) are a different population and must not be pooled
naively.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pdf_to_images import pdf_to_images
from parse_markscheme import parse_markscheme
from parse_question_paper import parse_question_paper
from annotator import merge
from database import init_db, paper_exists, insert_paper, get_stats


# Session codes as they appear in filenames, longest-first so "MJ R" wins over "MJ".
# Maps the code to (human-readable session, representative month).
SESSION_CODES = [
    ("MJ R", ("May/June (R)",         "June")),
    ("ON R", ("October/November (R)", "October")),
    ("Jan",  ("January",              "January")),
    ("Jun",  ("June",                 "June")),
    ("MJ",   ("May/June",             "June")),
    ("ON",   ("October/November",     "October")),
]
_CODE_ALT = "|".join(re.escape(c) for c, _ in SESSION_CODES)

# e.g. "Maths P2 MJ 2019 QP" / "Maths P2 MJ R 2024 QP"
PAPER_PATTERN = re.compile(
    rf"(?P<unit>P\d|S\d|M\d)\s+(?P<code>{_CODE_ALT})\s+(?P<year>\d{{4}})\s+QP",
    re.IGNORECASE,
)


def spec_version_for_year(year) -> str | None:
    """Edexcel IAL: 2018 spec (P-units) from 2019 exams onward; 2008 spec (C-units) before."""
    if not year:
        return None
    return "IAL_2018" if year >= 2019 else "IAL_2008"


def find_pairs(folder: str) -> list[dict]:
    """
    Recursively scan the folder tree for question papers and match each to its
    mark scheme (required) and examiner report (optional) by swapping the
    trailing QP token. Returns dicts with: paper_file, ms_file, er_file (or
    None), paper_id, meta.
    """
    folder = Path(folder)
    papers = sorted(folder.rglob("*QP.pdf"))
    pairs = []

    for paper_file in papers:
        ms_file = paper_file.with_name(paper_file.name[:-len("QP.pdf")] + "MS.pdf")
        er_file = paper_file.with_name(paper_file.name[:-len("QP.pdf")] + "ER.pdf")

        if not ms_file.exists():
            print(f"  Warning: no mark scheme found for {paper_file.name}, skipping")
            continue

        meta = parse_filename_meta(paper_file.name)
        if meta["unit"] == "Unknown":
            print(f"  Warning: could not parse metadata from {paper_file.name}, skipping")
            continue

        # paper_id: unit_year_code, e.g. P2_2019_MJ, P2_2024_MJ_R
        code_slug = meta["code"].replace(" ", "_")
        paper_id = f"{meta['unit']}_{meta['year']}_{code_slug}"

        pairs.append({
            "paper_file": str(paper_file),
            "ms_file":    str(ms_file),
            "er_file":    str(er_file) if er_file.exists() else None,
            "paper_id":   paper_id,
            "meta":       meta,
        })

    return pairs


def parse_filename_meta(filename: str) -> dict:
    m = PAPER_PATTERN.search(filename)
    if m:
        unit = m.group("unit").upper()
        code = re.sub(r"\s+", " ", m.group("code").upper()).strip()
        year = int(m.group("year"))
        session_label, month = dict((c.upper(), v) for c, v in SESSION_CODES)[code]
        return {
            "syllabus":     "Edexcel IAL",
            "unit":         unit,
            "code":         code,
            "session":      f"{session_label} {year}",
            "year":         year,
            "month":        month,
            "spec_version": spec_version_for_year(year),
        }
    return {"syllabus": "Unknown", "unit": "Unknown", "code": None,
            "session": filename, "year": None, "spec_version": None}


def ingest_pair(pair: dict, image_base: str, parsed_base: str, force: bool = False):
    paper_id   = pair["paper_id"]
    meta       = pair["meta"]
    paper_file = pair["paper_file"]
    ms_file    = pair["ms_file"]

    print(f"\n  [{paper_id}]  {meta.get('session', '?')}")

    if not force and paper_exists(paper_id):
        print(f"    Already in database, skipping. (use --reparse to force)")
        return

    image_base  = Path(image_base)
    parsed_base = Path(parsed_base)

    # Step 1: PDF → images
    print(f"    Converting PDFs to images...")
    ms_images    = pdf_to_images(ms_file,    str(image_base / paper_id / "ms"))
    paper_images = pdf_to_images(paper_file, str(image_base / paper_id / "paper"))
    print(f"    Mark scheme: {len(ms_images)} pages, Question paper: {len(paper_images)} pages")

    # Step 2: Parse with Claude
    print(f"    Parsing mark scheme...")
    ms_json_path    = str(parsed_base / f"{paper_id}_ms.json")
    parse_markscheme(ms_images, structured=True, output_path=ms_json_path)

    print(f"    Parsing question paper...")
    paper_json_path = str(parsed_base / f"{paper_id}_paper.json")
    parse_question_paper(paper_images, output_path=paper_json_path)

    # Step 3: Merge + annotate
    print(f"    Merging and computing solvability signals...")
    annotated_path = str(parsed_base / f"{paper_id}_annotated.json")
    records = merge(paper_json_path, ms_json_path, output_path=annotated_path)

    # Filter out any None question numbers (cover pages etc.)
    records = [r for r in records if r.get("question_number") not in (None, "None", "unknown")]

    # Step 4: Store in DB
    meta["paper_file"] = paper_file
    meta["ms_file"]    = ms_file
    meta["er_file"]    = pair.get("er_file")
    insert_paper(paper_id, meta, records)
    print(f"    Stored {len(records)} questions in database")


def ingest_all(pastpapers_folder: str, force: bool = False):
    base      = Path(__file__).parent.parent
    image_dir = base / "data" / "images"
    parse_dir = base / "data" / "parsed"

    init_db()

    print("Scanning for paper pairs...")
    pairs = find_pairs(pastpapers_folder)
    print(f"Found {len(pairs)} pair(s):\n")
    for p in pairs:
        status = "already parsed" if paper_exists(p["paper_id"]) and not force else "will parse"
        print(f"  {p['paper_id']:30s}  {status}")

    print(f"\nProcessing...")
    for pair in pairs:
        ingest_pair(pair, str(image_dir), str(parse_dir), force=force)

    stats = get_stats()
    print(f"\n{'━'*50}")
    print(f"  Question bank updated:")
    print(f"  {stats['papers']} papers  |  {stats['questions']} questions  |  {stats['parts']} parts")
    print(f"{'━'*50}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder",  default=str(Path(__file__).parent.parent / "pastpapers"))
    parser.add_argument("--reparse", action="store_true")
    args = parser.parse_args()

    ingest_all(args.folder, force=args.reparse)
