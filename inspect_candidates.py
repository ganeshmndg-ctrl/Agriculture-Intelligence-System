import json
import re
from pathlib import Path

rich_folder = Path("data/rich_blocks")


def looks_like_headline(block):
    text = block["text"].strip()
    font_size = block["max_font_size"]

    # Rule 1: headline should have reasonably large text
    if font_size < 13:
        return False

    # Rule 2: ignore obvious newspaper furniture
    ignored_phrases = [
        "published simultaneously",
        "business-standard.com",
        "www.economictimes.com",
        "to our readers",
        "newsbreak",
        "nk daily news",
        "group +91",
        "www.",
    ]

    text_lower = text.lower()

    for phrase in ignored_phrases:
        if phrase in text_lower:
            return False

    # Rule 3: ignore mostly numeric/contact-number text
    letters = sum(char.isalpha() for char in text)
    digits = sum(char.isdigit() for char in text)

    if letters == 0:
        return False

    if digits > letters * 2:
        return False

    # Rule 4: headline should contain at least 3 words
    words = text.split()

    if len(words) < 3:
        return False

    # Rule 5: ignore very long newspaper metadata blocks
    if len(text) > 250:
        return False

    return True


for json_file in rich_folder.glob("*_rich_blocks.json"):

    print("=" * 80)
    print("NEWSPAPER:", json_file.name)
    print("=" * 80)

    with open(json_file, "r", encoding="utf-8") as file:
        blocks = json.load(file)

    # Still testing only page 3
    page_blocks = [
        block
        for block in blocks
        if block["page"] == 3
    ]

    candidates = [
        block
        for block in page_blocks
        if looks_like_headline(block)
    ]

    candidates.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    print("Headline candidates:", len(candidates))
    print()

    for block in candidates:

        print(
            f"Block {block['block']:3} | "
            f"font={block['max_font_size']:5.1f} | "
            f"bold={block['bold_ratio']:4.2f} | "
            f"lines={block['line_count']:2} | "
            f"x={block['x0']:6.1f} | "
            f"y={block['y0']:6.1f}"
        )

        print("   ", block["text"])
        print()