"""
Parses question paper images using Claude vision.
Extracts question text, mark allocations, topic signals, and given values.
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

QUESTION_PAPER_PROMPT = """You are parsing pages from an A-level math exam paper.

For each question or question part visible on this page, extract the following and return as JSON.

Return a JSON object with this structure:
{
  "questions": [
    {
      "question_number": "1",
      "topic_signals": ["arithmetic_series"],
      "given_values": ["2", "5", "8", "254"],
      "given_value_types": ["integer"],
      "parts": [
        {
          "part": "a",
          "question_text": "find the number of terms in the series",
          "marks": 2,
          "command_word": "find"
        },
        {
          "part": "b",
          "question_text": "find the sum of the series",
          "marks": 2,
          "command_word": "find"
        }
      ]
    }
  ]
}

Rules:
- topic_signals: list of syllabus topics you can infer from the question (e.g. "differentiation",
  "binomial_expansion", "logarithms", "geometric_series", "coordinate_geometry", "integration",
  "trigonometric_identities", "proof", "polynomials")
- given_values: the numerical/algebraic values stated in the question as inputs
- given_value_types: "integer", "rational", "irrational", "algebraic" — describe the input number field
- command_word: the verb used ("find", "show", "prove", "state", "hence", "use calculus", etc.)
- If the page has no question content (instructions, blank), return {"questions": []}
- Use null for any field you cannot determine
- Do not include commentary outside the JSON block"""


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def parse_page(image_path: str) -> dict:
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
                    {"type": "text", "text": QUESTION_PAPER_PROMPT},
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"  Warning: could not parse JSON from page {image_path}")
        return {"questions": [], "raw": raw}


def merge_pages(page_results: list[dict]) -> dict:
    merged: dict[str, dict] = {}

    for page in page_results:
        for q in page.get("questions", []):
            qnum = str(q.get("question_number", "unknown"))
            if qnum not in merged:
                merged[qnum] = {
                    "question_number": qnum,
                    "topic_signals": q.get("topic_signals", []),
                    "given_values": q.get("given_values", []),
                    "given_value_types": q.get("given_value_types", []),
                    "parts": [],
                }

            existing_parts = {p["part"]: p for p in merged[qnum]["parts"]}
            for part in q.get("parts", []):
                if part.get("part") not in existing_parts:
                    merged[qnum]["parts"].append(part)

    return {
        "questions": sorted(merged.values(), key=lambda q: q["question_number"])
    }


def parse_question_paper(image_paths: list[str], output_path: str = None) -> dict:
    page_results = []
    for i, path in enumerate(image_paths, start=1):
        print(f"  Parsing page {i}/{len(image_paths)}: {Path(path).name}")
        result = parse_page(path)
        page_results.append(result)

    merged = merge_pages(page_results)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(merged, f, indent=2)
        print(f"\n  Written to {output_path}")

    return merged


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from pdf_to_images import pdf_to_images

    base = Path(__file__).parent.parent
    paper_pdf = base / "pastpapers" / "Edexcel International A Level (IAL) Maths P2 January 2025 Paper.pdf"
    image_dir = base / "data" / "images" / "paper"

    print("Step 1: Converting question paper PDF to images...")
    images = pdf_to_images(str(paper_pdf), str(image_dir))

    print("\nStep 2: Parsing question paper pages with Claude...")
    result = parse_question_paper(
        images,
        output_path=str(base / "data" / "parsed" / "paper_WMA12_2501.json"),
    )

    print(f"\nExtracted {len(result['questions'])} questions:")
    for q in result["questions"]:
        topics = ", ".join(q.get("topic_signals", []))
        parts_summary = ", ".join(
            f"{p['part']}({p.get('marks', '?')}m)" for p in q["parts"]
        )
        print(f"  Q{q['question_number']} [{topics}]: {parts_summary}")
