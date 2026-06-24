"""
Converts a PDF file into a list of PNG images, one per page.
Returns the image paths so downstream parsers can process them.
"""

import os
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image


def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 200) -> list[str]:
    """
    Renders each page of a PDF as a PNG and saves to output_dir.
    Returns sorted list of output image paths.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem.replace(" ", "_")
    pages = convert_from_path(str(pdf_path), dpi=dpi)

    paths = []
    for i, page in enumerate(pages, start=1):
        out_path = output_dir / f"{stem}_page{i:03d}.png"
        page.save(str(out_path), "PNG")
        paths.append(str(out_path))
        print(f"  Saved page {i}/{len(pages)}: {out_path.name}")

    return paths


if __name__ == "__main__":
    import sys

    base = Path(__file__).parent.parent
    papers = {
        "paper": base / "pastpapers" / "Edexcel International A Level (IAL) Maths P2 January 2025 Paper.pdf",
        "markscheme": base / "pastpapers" / "Edexcel International A Level (IAL) Maths P2 January 2025 MS.pdf",
    }

    for label, pdf in papers.items():
        print(f"\nConverting {label}...")
        paths = pdf_to_images(str(pdf), str(base / "data" / "images" / label))
        print(f"  → {len(paths)} pages written")
