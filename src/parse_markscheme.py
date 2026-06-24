"""
Parses mark scheme images using Claude vision.

For structured Edexcel-style mark schemes: extracts M1/dM1/A1/B1 counts,
worked solution steps, and final answers per question part.

For unstructured mark schemes (handwritten, other formats): falls back to
identifying significant steps by technique name rather than mark notation.
"""

import base64
import json
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

STRUCTURED_PROMPT = """You are parsing pages from an Edexcel A-level mark scheme.

For each question part visible on this page, extract the following and return as JSON.
If a question continues from a previous page or continues onto the next, extract what is visible.

Return a JSON object with this structure:
{
  "questions": [
    {
      "question_number": "1",
      "parts": [
        {
          "part": "a",
          "marks_total": 2,
          "mark_breakdown": {"M1": 1, "dM1": 0, "A1": 1, "B1": 0},
          "significant_steps": 1,
          "worked_steps": ["254 = 2 + 3(n-1) => n = 85"],
          "final_answer": "85",
          "answer_type": "integer",
          "notes": "any special marker notes worth keeping"
        }
      ]
    }
  ]
}

Rules:
- significant_steps = count of M1 + count of dM1 marks (not A1 or B1)
- worked_steps: list each distinct method step from the mark scheme solution, in order
- answer_type: one of "integer", "rational", "irrational", "expression", "proof", "coordinates"
- If the page has no mark scheme content (e.g. blank page, instructions), return {"questions": []}
- Use null for any field you cannot determine
- Do not include commentary outside the JSON block"""

UNSTRUCTURED_PROMPT = """You are analyzing a worked math solution (possibly handwritten or from a non-standard source).

Identify each distinct mathematical technique or method applied. These are "significant steps" —
not trivial rearrangements, but named operations like: differentiating, applying the quadratic formula,
taking logarithms of both sides, using a trig identity, integrating, applying a named theorem, etc.

Return a JSON object with this structure:
{
  "questions": [
    {
      "question_number": "1",
      "parts": [
        {
          "part": "a",
          "significant_steps": 2,
          "worked_steps": ["sets up equation using volume constraint", "differentiates and sets to zero"],
          "final_answer": "x = 3.76",
          "answer_type": "irrational",
          "notes": null
        }
      ]
    }
  ]
}

Rules:
- Be conservative: when in doubt about whether something is a significant step, count it
- worked_steps: plain English description of each step
- answer_type: one of "integer", "rational", "irrational", "expression", "proof", "coordinates"
- If the page has no solution content, return {"questions": []}"""


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def parse_page(image_path: str, structured: bool = True) -> dict:
    """Send a single page image to Claude and return parsed JSON."""
    prompt = STRUCTURED_PROMPT if structured else UNSTRUCTURED_PROMPT

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": encode_image(image_path),
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"  Warning: could not parse JSON from page {image_path}")
        print(f"  Raw response: {raw[:200]}")
        return {"questions": [], "raw": raw}


def merge_pages(page_results: list[dict]) -> dict:
    """
    Merge per-page results into a single document-level dict.
    Questions that span pages are merged by question_number.
    """
    merged: dict[str, dict] = {}

    for page in page_results:
        for q in page.get("questions", []):
            qnum = str(q.get("question_number", "unknown"))
            if qnum not in merged:
                merged[qnum] = {"question_number": qnum, "parts": []}

            existing_parts = {p["part"]: p for p in merged[qnum]["parts"]}
            for part in q.get("parts", []):
                part_label = part.get("part", "?")
                if part_label not in existing_parts:
                    merged[qnum]["parts"].append(part)

    return {
        "questions": sorted(merged.values(), key=lambda q: q["question_number"])
    }


def parse_markscheme(image_paths: list[str], structured: bool = True, output_path: str = None) -> dict:
    """
    Parse a full mark scheme from its page images.
    Returns merged JSON and optionally writes to output_path.
    """
    page_results = []
    for i, path in enumerate(image_paths, start=1):
        print(f"  Parsing page {i}/{len(image_paths)}: {Path(path).name}")
        result = parse_page(path, structured=structured)
        page_results.append(result)

    merged = merge_pages(page_results)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(merged, f, indent=2)
        print(f"\n  Written to {output_path}")

    return merged


if __name__ == "__main__":
    from pdf_to_images import pdf_to_images

    base = Path(__file__).parent.parent
    ms_pdf = base / "pastpapers" / "Edexcel International A Level (IAL) Maths P2 January 2025 MS.pdf"
    image_dir = base / "data" / "images" / "markscheme"

    print("Step 1: Converting mark scheme PDF to images...")
    images = pdf_to_images(str(ms_pdf), str(image_dir))

    print("\nStep 2: Parsing mark scheme pages with Claude...")
    result = parse_markscheme(
        images,
        structured=True,
        output_path=str(base / "data" / "parsed" / "markscheme_WMA12_2501.json"),
    )

    print(f"\nExtracted {len(result['questions'])} questions:")
    for q in result["questions"]:
        parts_summary = ", ".join(
            f"{p['part']}({p.get('marks_total', '?')}m/{p.get('significant_steps', '?')}steps)"
            for p in q["parts"]
        )
        print(f"  Q{q['question_number']}: {parts_summary}")
