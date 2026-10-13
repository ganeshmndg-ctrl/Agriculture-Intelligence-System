import json
from pathlib import Path
from collections import defaultdict


# ============================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# GENERAL ARTICLE GROUPER V3
#
# Goal:
#   Convert newspaper PDF blocks into preliminary article
#   regions without using agriculture-specific filtering.
#
# Important:
#   This is a diagnostic/processing layer.
#   Gemini will NOT be used here.
#
# Internal block structure:
#   block_id
#   page
#   x0, y0, x1, y1
#   text
#
# Article structure:
#   headline
#   subheads
#   bylines
#   body
#   related_blocks
#   all_blocks
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
    / "grouped_all_articles_v3"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# SETTINGS
# ============================================================

# We first test the pages that we already inspected.
TEST_PAGES = {
    "BS Mumbai 16-09-2026": [1, 3, 4],
    "ET Mumbai 16-09-2026": [3, 9, 20],
}

# Minimum score for a candidate article headline.
HEADLINE_MIN_SCORE = 5

# Maximum vertical gap for normal article continuation.
MAX_VERTICAL_GAP = 120

# Maximum horizontal displacement for direct continuation.
MAX_X_SHIFT = 180

# Minimum body text length.
MIN_BODY_CHARS = 18

# Maximum number of blocks in one preliminary article.
MAX_ARTICLE_BLOCKS = 40


# ============================================================
# NOISE
# ============================================================

NOISE_TERMS = [
    "www.business-standard.com",
    "www.business-standard",
    "published simultaneously",
    "economic times",
    "the economic times",
    "group +91",
    "scan qr",
    "download app",
    "subscribe",
    "advertisement",
    "advertorial",
]


# ============================================================
# LABELS / PAGE FURNITURE
# ============================================================

LABEL_TERMS = [
    "in brief",
    "other news of the day",
    "stocks in the news",
    "to our readers",
    "leading the pack",
    "the fee map",
    "pressure signals",
    "crude shock",
    "market watch",
    "contents",
    "index",
]


# ============================================================
# LOAD
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    return " ".join(
        str(text).split()
    )


# ============================================================
# TEXT HELPERS
# ============================================================

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


def is_label(text):

    text = clean_text(text).lower()

    if not text:
        return True

    for term in LABEL_TERMS:

        if text == term:
            return True

    return False


# ============================================================
# INTERNAL BLOCK FORMAT
# ============================================================

def convert_block(block):

    return {
        "block_id": block["block"],
        "page": block["page"],
        "x0": float(block["x0"]),
        "y0": float(block["y0"]),
        "x1": float(block["x1"]),
        "y1": float(block["y1"]),
        "text": clean_text(block["text"]),
        "line_count": block.get("line_count", 0),
        "min_font_size": block.get(
            "min_font_size",
            0
        ),
        "max_font_size": block.get(
            "max_font_size",
            0
        ),
        "bold_ratio": block.get(
            "bold_ratio",
            0
        ),
    }


# ============================================================
# GEOMETRY
# ============================================================

def width(block):

    return max(
        0,
        block["x1"] - block["x0"]
    )


def height(block):

    return max(
        0,
        block["y1"] - block["y0"]
    )


def center_x(block):

    return (
        block["x0"]
        +
        block["x1"]
    ) / 2


def center_y(block):

    return (
        block["y0"]
        +
        block["y1"]
    ) / 2


def horizontal_overlap(a, b):

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

    smaller = min(
        width(a),
        width(b)
    )

    if smaller <= 0:
        return 0

    return overlap / smaller


def horizontal_distance(a, b):

    if a["x1"] < b["x0"]:
        return b["x0"] - a["x1"]

    if b["x1"] < a["x0"]:
        return a["x0"] - b["x1"]

    return 0


def vertical_gap(a, b):

    return b["y0"] - a["y1"]


# ============================================================
# HEADLINE SCORING
# ============================================================

def headline_score(block):

    text = block["text"]

    if not text:
        return -999

    if is_noise(text):
        return -999

    if is_label(text):
        return -999

    length = len(text)
    words = word_count(text)

    if length < 12:
        return -999

    if length > 180:
        return -999

    score = 0

    font = block["min_font_size"]
    max_font = block["max_font_size"]
    lines = block["line_count"]
    bold = block["bold_ratio"]

    # --------------------------------------------------------
    # Font
    # --------------------------------------------------------

    if max_font >= 18:
        score += 6

    elif max_font >= 15:
        score += 5

    elif max_font >= 13:
        score += 4

    elif max_font >= 11:
        score += 2

    # --------------------------------------------------------
    # Bold
    # --------------------------------------------------------

    if bold >= 0.5:
        score += 3

    elif bold >= 0.2:
        score += 2

    elif bold > 0:
        score += 1

    # --------------------------------------------------------
    # Length
    # --------------------------------------------------------

    if 20 <= length <= 110:
        score += 2

    elif length <= 150:
        score += 1

    # --------------------------------------------------------
    # Reasonable headline lines
    # --------------------------------------------------------

    if lines <= 3:
        score += 2

    elif lines <= 5:
        score += 1

    # --------------------------------------------------------
    # Avoid tiny labels
    # --------------------------------------------------------

    if words <= 2:
        score -= 2

    return score


# ============================================================
# BODY SCORE
# ============================================================

def body_score(
    headline,
    block
):

    text = block["text"]

    if not text:
        return -999

    if is_noise(text):
        return -999

    if is_label(text):
        return -999

    if len(text) < MIN_BODY_CHARS:
        return -999

    score = 0

    # --------------------------------------------------------
    # Must be after headline
    # --------------------------------------------------------

    gap = vertical_gap(
        headline,
        block
    )

    if gap < 0:
        return -999

    if gap <= 25:
        score += 5

    elif gap <= 50:
        score += 4

    elif gap <= 80:
        score += 3

    elif gap <= MAX_VERTICAL_GAP:
        score += 1

    else:
        return -999

    # --------------------------------------------------------
    # Horizontal relationship
    # --------------------------------------------------------

    overlap = horizontal_overlap(
        headline,
        block
    )

    distance = horizontal_distance(
        headline,
        block
    )

    if overlap >= 0.70:
        score += 5

    elif overlap >= 0.40:
        score += 4

    elif overlap >= 0.20:
        score += 2

    elif distance <= MAX_X_SHIFT:
        score += 1

    # --------------------------------------------------------
    # Body font usually smaller
    # --------------------------------------------------------

    if (
        block["min_font_size"]
        <
        headline["min_font_size"]
    ):
        score += 2

    # --------------------------------------------------------
    # Longer text is more likely body
    # --------------------------------------------------------

    if len(text) >= 80:
        score += 2

    elif len(text) >= 40:
        score += 1

    return score


# ============================================================
# CLASSIFY BLOCK TYPE
# ============================================================

def classify_block(
    block,
    article_headlines
):

    text = block["text"]

    if is_noise(text):
        return "NOISE"

    if is_label(text):
        return "LABEL"

    # Existing article headline
    for headline in article_headlines:

        if (
            headline["block_id"]
            ==
            block["block_id"]
        ):
            return "HEADLINE"

    # Very short text
    if len(text) < MIN_BODY_CHARS:
        return "SMALL_TEXT"

    # Possible body
    if (
        block["line_count"] >= 2
        and
        block["min_font_size"] <= 11
    ):
        return "BODY"

    # Possible caption / subhead
    if (
        block["line_count"] <= 2
        and
        len(text) < 100
    ):
        return "RELATED"

    return "BODY"


# ============================================================
# FIND HEADLINES
# ============================================================

def find_headlines(
    page_blocks
):

    candidates = []

    for block in page_blocks:

        score = headline_score(
            block
        )

        if score >= HEADLINE_MIN_SCORE:

            candidates.append(
                {
                    "block_id":
                        block["block_id"],

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

                    "score":
                        score,

                    "min_font_size":
                        block[
                            "min_font_size"
                        ],

                    "max_font_size":
                        block[
                            "max_font_size"
                        ],

                    "bold_ratio":
                        block[
                            "bold_ratio"
                        ],
                }
            )

    candidates.sort(
        key=lambda h: (
            h["y0"],
            h["x0"]
        )
    )

    return candidates


# ============================================================
# CHECK IF BLOCK IS PROTECTED BY ANOTHER HEADLINE
# ============================================================

def belongs_to_other_headline_region(
    headline,
    block,
    headlines
):

    for other in headlines:

        if (
            other["block_id"]
            ==
            headline["block_id"]
        ):
            continue

        # Other headline must occur above this block
        if other["y0"] >= block["y0"]:
            continue

        # Same/general horizontal region
        overlap = horizontal_overlap(
            other,
            block
        )

        distance = horizontal_distance(
            other,
            block
        )

        if (
            overlap >= 0.25
            or
            distance <= 40
        ):

            # If the other headline is substantially closer
            # to the block than our target headline,
            # the block likely belongs to the other article.
            target_distance = (
                block["y0"]
                -
                headline["y1"]
            )

            other_distance = (
                block["y0"]
                -
                other["y1"]
            )

            if (
                other_distance
                <
                target_distance
            ):

                return True

    return False


# ============================================================
# FIND ARTICLE BODY
# ============================================================

def find_article_blocks(
    headline,
    page_blocks,
    headlines
):

    scored = []

    for block in page_blocks:

        if (
            block["block_id"]
            ==
            headline["block_id"]
        ):
            continue

        # Another headline itself
        if any(
            h["block_id"]
            ==
            block["block_id"]
            for h in headlines
        ):
            continue

        # Prevent obvious cross-story contamination
        if belongs_to_other_headline_region(
            headline,
            block,
            headlines
        ):
            continue

        score = body_score(
            headline,
            block
        )

        if score < 7:
            continue

        scored.append(
            (
                score,
                block
            )
        )

    # --------------------------------------------------------
    # Sort by physical position
    # --------------------------------------------------------

    scored.sort(
        key=lambda item: (
            item[1]["y0"],
            item[1]["x0"]
        )
    )

    selected = []

    previous_blocks = [
        headline
    ]

    for score, block in scored:

        if len(selected) >= (
            MAX_ARTICLE_BLOCKS - 1
        ):
            break

        # ----------------------------------------------------
        # Determine whether this block continues from one
        # of the existing article blocks.
        # ----------------------------------------------------

        continuation = False

        for previous in previous_blocks:

            gap = vertical_gap(
                previous,
                block
            )

            if gap < 0:
                continue

            if gap > MAX_VERTICAL_GAP:
                continue

            overlap = horizontal_overlap(
                previous,
                block
            )

            distance = horizontal_distance(
                previous,
                block
            )

            if (
                overlap >= 0.20
                or
                distance <= MAX_X_SHIFT
            ):

                continuation = True
                break

        if not continuation:
            continue

        selected.append(
            block
        )

        previous_blocks.append(
            block
        )

    return selected


# ============================================================
# IDENTIFY SUBHEADS / BYLINES / RELATED BLOCKS
# ============================================================

def identify_special_blocks(
    headline,
    body_blocks
):

    subheads = []
    bylines = []
    related = []
    body = []

    for block in body_blocks:

        text = block["text"]
        lower = text.lower()

        # ----------------------------------------------------
        # Byline
        # ----------------------------------------------------

        if (
            "by "
            in lower[:30]
            and
            len(text) < 120
        ):

            bylines.append(
                block
            )

            continue

        # ----------------------------------------------------
        # Subheadline
        # ----------------------------------------------------

        if (
            block["line_count"] <= 3
            and
            len(text) < 180
            and
            block["min_font_size"]
            >= 9
        ):

            subheads.append(
                block
            )

            continue

        # ----------------------------------------------------
        # Short related item
        # ----------------------------------------------------

        if (
            len(text) < 60
            and
            block["line_count"] <= 2
        ):

            related.append(
                block
            )

            continue

        # ----------------------------------------------------
        # Normal body
        # ----------------------------------------------------

        body.append(
            block
        )

    return (
        subheads,
        bylines,
        related,
        body
    )


# ============================================================
# BUILD ARTICLE
# ============================================================

def build_article(
    headline,
    body_blocks
):

    (
        subheads,
        bylines,
        related,
        body
    ) = identify_special_blocks(
        headline,
        body_blocks
    )

    all_blocks = [
        headline
    ] + body_blocks

    all_blocks.sort(
        key=lambda b: (
            b["y0"],
            b["x0"]
        )
    )

    # --------------------------------------------------------
    # Body text
    # --------------------------------------------------------

    body_text = "\n\n".join(
        block["text"]
        for block in body
    )

    # --------------------------------------------------------
    # Subhead text
    # --------------------------------------------------------

    subhead_text = "\n\n".join(
        block["text"]
        for block in subheads
    )

    # --------------------------------------------------------
    # Byline
    # --------------------------------------------------------

    byline_text = "\n".join(
        block["text"]
        for block in bylines
    )

    # --------------------------------------------------------
    # Full article text
    # --------------------------------------------------------

    full_text = "\n\n".join(
        block["text"]
        for block in all_blocks
    )

    return {

        "page":
            headline["page"],

        "headline_block":
            headline["block_id"],

        "headline":
            headline["text"],

        "headline_score":
            headline["score"],

        "subheads":
            [
                b["text"]
                for b in subheads
            ],

        "bylines":
            [
                b["text"]
                for b in bylines
            ],

        "body_text":
            body_text,

        "related_blocks":
            [
                b["text"]
                for b in related
            ],

        "full_article_text":
            full_text,

        "block_count":
            len(all_blocks),

        "body_block_count":
            len(body),

        "blocks":
            [
                {
                    "block_id":
                        b["block_id"],

                    "source":
                        (
                            "headline"
                            if
                            b["block_id"]
                            ==
                            headline["block_id"]
                            else
                            "body"
                        ),

                    "x0":
                        b["x0"],

                    "y0":
                        b["y0"],

                    "x1":
                        b["x1"],

                    "y1":
                        b["y1"],

                    "text":
                        b["text"]
                }
                for b in all_blocks
            ]
    }


# ============================================================
# PROCESS PAGE
# ============================================================

def process_page(
    page_blocks,
    page_number
):

    # --------------------------------------------------------
    # Find probable headlines
    # --------------------------------------------------------

    headlines = find_headlines(
        page_blocks
    )

    # --------------------------------------------------------
    # Remove overlapping duplicate headlines
    #
    # If two headline candidates are physically almost
    # identical, keep the stronger one.
    # --------------------------------------------------------

    final_headlines = []

    for candidate in headlines:

        duplicate = False

        for existing in final_headlines:

            overlap = horizontal_overlap(
                candidate,
                existing
            )

            y_difference = abs(
                candidate["y0"]
                -
                existing["y0"]
            )

            if (
                overlap >= 0.60
                and
                y_difference <= 20
            ):

                duplicate = True

                if (
                    candidate["score"]
                    >
                    existing["score"]
                ):

                    final_headlines.remove(
                        existing
                    )

                    final_headlines.append(
                        candidate
                    )

                break

        if not duplicate:

            final_headlines.append(
                candidate
            )

    final_headlines.sort(
        key=lambda h: (
            h["y0"],
            h["x0"]
        )
    )

    # --------------------------------------------------------
    # Build articles
    # --------------------------------------------------------

    articles = []

    for headline in final_headlines:

        body_blocks = find_article_blocks(
            headline,
            page_blocks,
            final_headlines
        )

        article = build_article(
            headline,
            body_blocks
        )

        articles.append(
            article
        )

    return (
        final_headlines,
        articles
    )


# ============================================================
# PROCESS NEWSPAPER
# ============================================================

def process_newspaper(
    rich_file
):

    newspaper_name = (
        rich_file
        .stem
        .replace(
            "_rich_blocks",
            ""
        )
    )

    print()
    print(
        "=" * 90
    )

    print(
        newspaper_name
    )

    print(
        "=" * 90
    )

    rich_raw = load_json(
        rich_file
    )

    blocks = [
        convert_block(
            block
        )
        for block in rich_raw
    ]

    pages = defaultdict(list)

    for block in blocks:

        pages[
            block["page"]
        ].append(
            block
        )

    pages_to_process = (
        TEST_PAGES.get(
            newspaper_name,
            sorted(
                pages.keys()
            )
        )
    )

    all_articles = []

    diagnostics = []

    for page_number in pages_to_process:

        if page_number not in pages:

            continue

        page_blocks = pages[
            page_number
        ]

        page_blocks.sort(
            key=lambda b: (
                b["y0"],
                b["x0"]
            )
        )

        headlines, articles = process_page(
            page_blocks,
            page_number
        )

        all_articles.extend(
            articles
        )

        # ----------------------------------------------------
        # Console diagnostic
        # ----------------------------------------------------

        print()
        print(
            f"PAGE {page_number}"
        )

        print(
            f"Blocks: "
            f"{len(page_blocks)}"
        )

        print(
            f"Probable articles: "
            f"{len(articles)}"
        )

        print(
            "-" * 90
        )

        for index, article in enumerate(
            articles,
            start=1
        ):

            print(
                f"[{index}] "
                f"B{article['headline_block']} "
                f"| "
                f"{article['headline']}"
            )

            print(
                f"    body blocks: "
                f"{article['body_block_count']}"
            )

            print(
                f"    all blocks: "
                f"{article['block_count']}"
            )

            print(
                f"    blocks: "
                f"{[b['block_id'] for b in article['blocks']]}"
            )

        diagnostics.append(
            {
                "page":
                    page_number,

                "total_blocks":
                    len(page_blocks),

                "headline_count":
                    len(headlines),

                "article_count":
                    len(articles),

                "articles":
                    articles
            }
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_file = (
        OUTPUT_DIR
        /
        f"{newspaper_name}"
        "_grouped_v3.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            diagnostics,
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

    rich_files = sorted(
        RICH_DIR.glob(
            "*_rich_blocks.json"
        )
    )

    if not rich_files:

        print(
            "No rich block files found."
        )

        return

    print(
        f"Found "
        f"{len(rich_files)} "
        f"rich-block file(s)."
    )

    for rich_file in rich_files:

        process_newspaper(
            rich_file
        )

    print()
    print(
        "=" * 90
    )

    print(
        "GENERAL ARTICLE GROUPING V3 COMPLETE"
    )

    print(
        "=" * 90
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()