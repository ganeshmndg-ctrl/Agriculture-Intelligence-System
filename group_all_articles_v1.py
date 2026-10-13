import json
from pathlib import Path
from collections import defaultdict


# ============================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# GENERAL ARTICLE GROUPING V2.1
#
# IMPORTANT DATA STRUCTURES
#
# Candidate headline:
#     block_number
#
# Rich block:
#     block
#
# This script explicitly converts candidate headlines into
# a common internal structure before grouping.
# ============================================================


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RICH_DIR = BASE_DIR / "data" / "rich_blocks"

CANDIDATE_DIR = (
    BASE_DIR
    / "data"
    / "all_article_candidates"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "grouped_all_articles_v2"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# SETTINGS
# ============================================================

# We are testing the first 10 pages first.
MAX_PAGES = 10

# Maximum headline candidates for diagnostic run.
MAX_HEADLINES = 30

# Maximum vertical distance between related blocks.
MAX_VERTICAL_GAP = 100

# Minimum characters for a body block.
MIN_BODY_CHARS = 15


# ============================================================
# NOISE
# ============================================================

NOISE_TERMS = [

    "www.business-standard.com",
    "www.business-standard",
    "business standard",
    "published simultaneously",

    "economic times",
    "the economic times",
    "group +91",

    "whatsapp",
    "scan qr",
    "subscribe",
    "download app",
    "click here",
    "advertisement",
    "advertorial",

]


# ============================================================
# SECTION / LABEL TERMS
# ============================================================

SECTION_TERMS = [

    "in brief",
    "in focus",
    "the big story",
    "the bottom line",
    "opinion",
    "columns",
    "contents",
    "index",
    "market watch",
    "leading the pack",
    "the fee map",

]


# ============================================================
# BASIC HELPERS
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def clean_text(text):

    if not text:
        return ""

    return " ".join(
        str(text).split()
    )


def word_count(text):

    return len(
        clean_text(text).split()
    )


def is_noise(text):

    text = clean_text(text).lower()

    if not text:
        return True

    for term in NOISE_TERMS:

        if term in text:
            return True

    return False


def is_section_label(text):

    text = clean_text(text).lower()

    if not text:
        return True

    for term in SECTION_TERMS:

        if text == term:
            return True

    return False


# ============================================================
# HEADLINE DETECTION
# ============================================================

def is_probable_headline(block):

    text = clean_text(
        block.get(
            "text",
            ""
        )
    )

    if not text:
        return False

    if is_noise(text):
        return False

    if is_section_label(text):
        return False

    if len(text) < 12:
        return False

    if len(text) > 150:
        return False

    if block.get(
        "line_count",
        0
    ) > 5:
        return False

    font = block.get(
        "min_font_size",
        0
    )

    max_font = block.get(
        "max_font_size",
        0
    )

    bold = block.get(
        "bold_ratio",
        0
    )

    # Strong headline
    if max_font >= 15:
        return True

    # Standard headline
    if font >= 12:
        return True

    # Moderately large + bold
    if (
        font >= 10
        and
        bold > 0.15
        and
        len(text) < 100
    ):
        return True

    # Short headline
    if (
        font >= 10
        and
        len(text) < 70
    ):
        return True

    return False


# ============================================================
# CONVERT CANDIDATE TO INTERNAL HEADLINE STRUCTURE
# ============================================================

def convert_candidate_to_headline(
    candidate
):

    """
    Candidate files use:
        block_number

    Internally we use:
        block_id

    This eliminates the repeated block/block_number problem.
    """

    return {

        "block_id":
            candidate[
                "block_number"
            ],

        "page":
            candidate["page"],

        "x0":
            candidate["x0"],

        "y0":
            candidate["y0"],

        "x1":
            candidate["x1"],

        "y1":
            candidate["y1"],

        "text":
            candidate["text"],

        "min_font_size":
            candidate.get(
                "min_font_size",
                0
            ),

        "max_font_size":
            candidate.get(
                "max_font_size",
                0
            ),

        "bold_ratio":
            candidate.get(
                "bold_ratio",
                0
            )

    }


# ============================================================
# CONVERT RICH BLOCK TO INTERNAL STRUCTURE
# ============================================================

def convert_rich_block(
    block
):

    """
    Rich files use:
        block

    Internally we use:
        block_id
    """

    return {

        "block_id":
            block["block"],

        "page":
            block["page"],

        "x0":
            block["x0"],

        "y0":
            block["y0"],

        "x1":
            block["x1"],

        "y1":
            block["y1"],

        "text":
            block["text"],

        "min_font_size":
            block.get(
                "min_font_size",
                0
            ),

        "max_font_size":
            block.get(
                "max_font_size",
                0
            ),

        "bold_ratio":
            block.get(
                "bold_ratio",
                0
            ),

        "line_count":
            block.get(
                "line_count",
                0
            )

    }


# ============================================================
# HORIZONTAL OVERLAP
# ============================================================

def horizontal_overlap(
    a,
    b
):

    left = max(
        a["x0"],
        b["x0"]
    )

    right = min(
        a["x1"],
        b["x1"]
    )

    overlap = max(
        0,
        right - left
    )

    width_a = max(
        1,
        a["x1"] - a["x0"]
    )

    width_b = max(
        1,
        b["x1"] - b["x0"]
    )

    return (
        overlap
        /
        min(
            width_a,
            width_b
        )
    )


# ============================================================
# SAME COLUMN
# ============================================================

def same_column(
    headline,
    block
):

    overlap = horizontal_overlap(
        headline,
        block
    )

    if overlap >= 0.65:
        return 3

    if overlap >= 0.35:
        return 2

    x_difference = abs(
        headline["x0"]
        -
        block["x0"]
    )

    if x_difference <= 25:
        return 1

    return 0


# ============================================================
# BODY BLOCK SCORE
# ============================================================

def score_body_block(
    headline,
    block
):

    text = clean_text(
        block["text"]
    )

    if not text:
        return -999

    if is_noise(text):
        return -999

    if len(text) < MIN_BODY_CHARS:
        return -999

    # Don't use obvious headlines as body
    if is_probable_headline(
        block
    ):
        return -999

    # --------------------------------------------------------
    # Vertical relationship
    # --------------------------------------------------------

    gap = (
        block["y0"]
        -
        headline["y1"]
    )

    if gap < 0:
        return -999

    if gap > MAX_VERTICAL_GAP:
        return -999

    score = 0

    if gap <= 20:
        score += 5

    elif gap <= 40:
        score += 4

    elif gap <= 70:
        score += 3

    else:
        score += 1

    # --------------------------------------------------------
    # Column relationship
    # --------------------------------------------------------

    column_score = same_column(
        headline,
        block
    )

    score += (
        column_score * 3
    )

    # --------------------------------------------------------
    # X alignment
    # --------------------------------------------------------

    x_difference = abs(
        headline["x0"]
        -
        block["x0"]
    )

    if x_difference <= 10:
        score += 3

    elif x_difference <= 25:
        score += 2

    elif x_difference <= 50:
        score += 1

    # --------------------------------------------------------
    # Font relationship
    # --------------------------------------------------------

    headline_font = headline.get(
        "min_font_size",
        0
    )

    block_font = block.get(
        "min_font_size",
        0
    )

    if (
        headline_font > 0
        and
        block_font < headline_font
    ):
        score += 2

    return score


# ============================================================
# FIND BODY BLOCKS
# ============================================================

def find_body_blocks(
    headline,
    page_blocks,
    page_headlines
):

    candidates = []

    headline_id = headline[
        "block_id"
    ]

    for block in page_blocks:

        block_id = block[
            "block_id"
        ]

        # ----------------------------------------------------
        # Don't attach the headline itself.
        # ----------------------------------------------------

        if block_id == headline_id:
            continue

        # ----------------------------------------------------
        # Don't attach another headline.
        # ----------------------------------------------------

        if any(
            h["block_id"] == block_id
            for h in page_headlines
        ):
            continue

        score = score_body_block(
            headline,
            block
        )

        if score < 7:
            continue

        candidates.append(
            (
                score,
                block["y0"],
                block["x0"],
                block
            )
        )

    # --------------------------------------------------------
    # Sort physically.
    # --------------------------------------------------------

    candidates.sort(
        key=lambda x: (
            x[1],
            x[2]
        )
    )

    selected = []

    previous_bottom = (
        headline["y1"]
    )

    for (
        score,
        y0,
        x0,
        block
    ) in candidates:

        gap = (
            block["y0"]
            -
            previous_bottom
        )

        # First body block
        if not selected:

            if gap > MAX_VERTICAL_GAP:
                continue

        # Once an article starts, stop when the physical
        # continuity becomes too large.
        else:

            if gap > MAX_VERTICAL_GAP:
                break

        selected.append(
            block
        )

        previous_bottom = block[
            "y1"
        ]

    return selected


# ============================================================
# BUILD ARTICLE
# ============================================================

def build_article(
    headline,
    body_blocks
):

    combined = []

    # Headline
    combined.append(
        {
            "block_id":
                headline["block_id"],

            "source":
                "headline",

            "x0":
                headline["x0"],

            "y0":
                headline["y0"],

            "x1":
                headline["x1"],

            "y1":
                headline["y1"],

            "text":
                headline["text"]
        }
    )

    # Body
    for block in body_blocks:

        combined.append(
            {
                "block_id":
                    block["block_id"],

                "source":
                    "body",

                "x0":
                    block["x0"],

                "y0":
                    block["y0"],

                "x1":
                    block["x1"],

                "y1":
                    block["y1"],

                "text":
                    block["text"]
            }
        )

    # Reading order
    combined.sort(
        key=lambda b: (
            b["y0"],
            b["x0"]
        )
    )

    # Article text
    text_parts = []

    for block in combined:

        text = clean_text(
            block["text"]
        )

        if text:

            text_parts.append(
                text
            )

    article_text = "\n\n".join(
        text_parts
    )

    return {

        "page":
            headline["page"],

        "headline_block":
            headline["block_id"],

        "headline":
            clean_text(
                headline["text"]
            ),

        "body_block_count":
            len(body_blocks),

        "total_block_count":
            len(combined),

        "blocks":
            combined,

        "article_text":
            article_text

    }


# ============================================================
# PROCESS NEWSPAPER
# ============================================================

def process_newspaper(
    candidate_file
):

    print()
    print("=" * 70)
    print(candidate_file.name)
    print("=" * 70)

    # --------------------------------------------------------
    # Load files
    # --------------------------------------------------------

    candidates_raw = load_json(
        candidate_file
    )

    rich_file = (
        RICH_DIR
        /
        candidate_file.name
    )

    if not rich_file.exists():

        print(
            "ERROR: Rich block file not found:"
        )

        print(
            rich_file
        )

        return

    rich_raw = load_json(
        rich_file
    )

    print(
        f"Total rich blocks: "
        f"{len(rich_raw)}"
    )

    print(
        f"Raw headline candidates: "
        f"{len(candidates_raw)}"
    )

    # --------------------------------------------------------
    # Convert rich blocks
    # --------------------------------------------------------

    rich_blocks = []

    for block in rich_raw:

        rich_blocks.append(
            convert_rich_block(
                block
            )
        )

    # --------------------------------------------------------
    # Convert candidates
    # --------------------------------------------------------

    headlines = []

    for candidate in candidates_raw:

        text = clean_text(
            candidate["text"]
        )

        if is_noise(text):
            continue

        if is_section_label(text):
            continue

        if len(text) < 12:
            continue

        headline = (
            convert_candidate_to_headline(
                candidate
            )
        )

        headlines.append(
            headline
        )

    print(
        f"Filtered headline candidates: "
        f"{len(headlines)}"
    )

    # --------------------------------------------------------
    # Group blocks by page
    # --------------------------------------------------------

    blocks_by_page = defaultdict(list)

    for block in rich_blocks:

        blocks_by_page[
            block["page"]
        ].append(
            block
        )

    # --------------------------------------------------------
    # Group headlines by page
    # --------------------------------------------------------

    headlines_by_page = defaultdict(list)

    for headline in headlines:

        headlines_by_page[
            headline["page"]
        ].append(
            headline
        )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    for page in blocks_by_page:

        blocks_by_page[
            page
        ].sort(
            key=lambda b: (
                b["y0"],
                b["x0"]
            )
        )

    for page in headlines_by_page:

        headlines_by_page[
            page
        ].sort(
            key=lambda h: (
                h["y0"],
                h["x0"]
            )
        )

    # --------------------------------------------------------
    # Restrict to first N pages
    # --------------------------------------------------------

    headlines = [
        h
        for h in headlines
        if (
            MAX_PAGES is None
            or
            h["page"] <= MAX_PAGES
        )
    ]

    # --------------------------------------------------------
    # Sort candidates
    # --------------------------------------------------------

    headlines.sort(
        key=lambda h: (
            h["page"],
            h["y0"],
            h["x0"]
        )
    )

    # --------------------------------------------------------
    # Limit
    # --------------------------------------------------------

    headlines = headlines[
        :MAX_HEADLINES
    ]

    articles = []

    # --------------------------------------------------------
    # Process headlines
    # --------------------------------------------------------

    for index, headline in enumerate(
        headlines,
        start=1
    ):

        page = headline[
            "page"
        ]

        page_blocks = (
            blocks_by_page.get(
                page,
                []
            )
        )

        page_headlines = (
            headlines_by_page.get(
                page,
                []
            )
        )

        body_blocks = find_body_blocks(
            headline,
            page_blocks,
            page_headlines
        )

        article = build_article(
            headline,
            body_blocks
        )

        articles.append(
            article
        )

        # ----------------------------------------------------
        # Console
        # ----------------------------------------------------

        print()
        print(
            f"[{index}] "
            f"Page {page} | "
            f"Block "
            f"{headline['block_id']}"
        )

        print(
            "HEADLINE:"
        )

        print(
            headline["text"]
        )

        print(
            "BODY BLOCKS:"
        )

        print(
            [
                b["block_id"]
                for b in body_blocks
            ]
        )

        print(
            f"BODY COUNT: "
            f"{len(body_blocks)}"
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    newspaper_name = (
        candidate_file
        .stem
        .replace(
            "_rich_blocks",
            ""
        )
    )

    output_file = (
        OUTPUT_DIR
        /
        f"{newspaper_name}"
        "_grouped_v2.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            articles,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(
        "Saved:"
    )

    print(
        output_file
    )


# ============================================================
# MAIN
# ============================================================

def main():

    candidate_files = sorted(
        CANDIDATE_DIR.glob(
            "*.json"
        )
    )

    if not candidate_files:

        print(
            "No candidate files found."
        )

        return

    print(
        f"Found "
        f"{len(candidate_files)} "
        f"candidate file(s)."
    )

    for candidate_file in candidate_files:

        process_newspaper(
            candidate_file
        )

    print()
    print("=" * 70)
    print(
        "GENERAL ARTICLE GROUPING V2.1 COMPLETE"
    )
    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()