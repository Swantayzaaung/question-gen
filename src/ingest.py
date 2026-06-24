"""
Batch ingest pipeline. Scans a folder of PDF pairs, parses any not yet in the
database, and stores results in the SQLite question bank.

Pair matching: looks for files sharing the same name prefix up to "Paper" / "MS".
E.g. "... P2 January 2023 Paper.pdf" matches "... P2 January 2023 MS.pdf"
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


PAPER_PATTERN = re.compile(
    r"(?P<syllabus>.+?)\s+(?P<unit>P\d|S\d|M\d)\s+(?P<session>\w+ \d{4})\s+Paper",
    re.IGNORECASE,
)


def find_pairs(folder: str) -> list[dict]:
    """
    Scan folder for (paper, markscheme) PDF pairs.
    Returns list of dicts with keys: paper_file, ms_file, paper_id, meta.
    """
    folder = Path(folder)
    papers = sorted(folder.glob("*Paper*.pdf"))
    pairs = []

    for paper_file in papers:
        # Derive expected MS filename by replacing "Paper" with "MS"
        ms_name = re.sub(r"Paper", "MS", paper_file.name, flags=re.IGNORECASE)
        ms_file = folder / ms_name

        if not ms_file.exists():
            print(f"  Warning: no mark scheme found for {paper_file.name}, skipping")
            continue

        # Parse metadata from filename
        meta = parse_filename_meta(paper_file.name)
        paper_id = f"{meta['unit']}_{meta['session'].replace(' ', '_')}"

        pairs.append({
            "paper_file": str(paper_file),
            "ms_file":    str(ms_file),
            "paper_id":   paper_id,
            "meta":       meta,
        })

    return pairs


def parse_filename_meta(filename: str) -> dict:
    m = PAPER_PATTERN.search(filename)
    if m:
        session = m.group("session")
        parts = session.split()
        return {
            "syllabus": "Edexcel IAL",
            "unit":     m.group("unit").upper(),
            "session":  session,
            "year":     int(parts[-1]) if parts[-1].isdigit() else None,
            "month":    parts[0] if len(parts) > 1 else None,
        }
    return {"syllabus": "Unknown", "unit": "Unknown", "session": filename, "year": None}


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
