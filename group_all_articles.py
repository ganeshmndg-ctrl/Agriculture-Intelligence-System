import json
from pathlib import Path


# ============================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# GENERAL ARTICLE HEADLINE DETECTION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RICH_DIR = BASE_DIR / "data" / "rich_blocks"
OUTPUT_DIR = BASE_DIR / "data" / "all_article_candidates"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# SETTINGS
# ============================================================

# Ignore obvious newspaper furniture / repeated navigation text
IGNORE_TERMS = [
    "www.business-standard.com",
    "www.business-standard",
    "economic times",
    "the economic times",
    "whatsapp",
    "scan qr",
    "subscribe",
    "advertisement",
    "follow us",
    "click here",
    "download app",
]


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_text(text):
    if not text:
        return ""

    return " ".join(text.split())


def is_noise(text):
    """
    Detect obvious newspaper furniture / non-headline text.
    """

    text_lower = text.lower()

    for term in IGNORE_TERMS:
        if term in text_lower:
            return True

    return False


def looks_like_headline(block):
    """
    Broad headline detector.

    This is intentionally conservative enough to avoid obvious
    newspaper furniture, but broad enough to capture headlines
    from agriculture, banking, finance, international, business,
    policy, technology, etc.
    """

    text = clean_text(block.get("text", ""))

    if not text:
        return False

    # Very long blocks are usually article bodies
    if len(text) > 160:
        return False

    # Extremely short fragments are usually labels
    if len(text) < 8:
        return False

    # Too many lines usually indicates body text
    if block.get("line_count", 0) > 5:
        return False

    # Ignore obvious newspaper furniture
    if is_noise(text):
        return False

    min_font = block.get("min_font_size", 0)
    max_font = block.get("max_font_size", 0)
    bold_ratio = block.get("bold_ratio", 0)

    # Headline-like font signals
    large_font = max_font >= 11
    medium_font = min_font >= 9

    # Some newspapers encode headlines using font families rather
    # than bold_ratio, so font size remains important.
    if large_font:
        return True

    if medium_font and bold_ratio > 0:
        return True

    # A short block with moderately large font
    if len(text) < 100 and min_font >= 10:
        return True

    return False


# ============================================================
# PROCESS NEWSPAPER
# ============================================================

def process_newspaper(rich_file):

    print("\n" + "=" * 70)
    print(rich_file.name)
    print("=" * 70)

    blocks = load_json(rich_file)

    print(f"Total blocks: {len(blocks)}")

    candidates = []

    for block in blocks:

        if not looks_like_headline(block):
            continue

        candidate = {
            "newspaper": "",
            "page": block["page"],

            # IMPORTANT:
            # Rich-block files use "block" as the block ID.
            # We preserve that ID here as "block_number".
            "block_number": block["block"],

            "text": clean_text(block["text"]),

            "x0": block["x0"],
            "y0": block["y0"],
            "x1": block["x1"],
            "y1": block["y1"],

            "min_font_size": block["min_font_size"],
            "max_font_size": block["max_font_size"],
            "bold_ratio": block["bold_ratio"],
            "line_count": block["line_count"],
        }

        candidates.append(candidate)

    print(
        f"Probable headline candidates: "
        f"{len(candidates)}"
    )

    # Save using same filename as the rich-block file
    output_file = OUTPUT_DIR / rich_file.name

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            candidates,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("Saved:")
    print(output_file)


# ============================================================
# MAIN
# ============================================================

def main():

    rich_files = sorted(
        RICH_DIR.glob("*_rich_blocks.json")
    )

    if not rich_files:

        print(
            "No rich-block files found in:"
        )

        print(RICH_DIR)

        return

    print(
        f"Found {len(rich_files)} newspaper file(s)."
    )

    for rich_file in rich_files:

        process_newspaper(rich_file)

    print("\n")
    print("=" * 70)
    print("GENERAL HEADLINE DETECTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()