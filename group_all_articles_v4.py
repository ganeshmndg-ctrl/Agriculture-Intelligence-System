import json
from pathlib import Path
from collections import defaultdict


# ============================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# GENERAL ARTICLE GROUPER V4 - PRODUCTION VERSION
#
# Purpose:
#   Group newspaper blocks into probable complete articles.
#
# Production improvements:
#   1. Uses headline candidates as article anchors
#   2. Removes obvious page furniture / advertisements
#   3. Prevents one article from stealing blocks from another
#   4. Allows an article to continue across physical columns
#   5. Treats subheads, bylines and fact boxes carefully
#   6. Does NOT use agriculture-specific filtering
#   7. Processes EVERY PAGE
#
# This version is designed for the automated daily pipeline.
# ============================================================


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RICH_DIR = (
    BASE_DIR
    / "data"
    / "rich_blocks"
)

CANDIDATE_DIR = (
    BASE_DIR
    / "data"
    / "all_article_candidates"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "grouped_all_articles_v4"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# SETTINGS
# ============================================================

MIN_HEADLINE_SCORE = 5

MAX_VERTICAL_DISTANCE = 500

MAX_HORIZONTAL_DISTANCE = 220

MIN_BODY_LENGTH = 20

MAX_BLOCKS = 50


# ============================================================
# PAGE FURNITURE / NOISE
# ============================================================

NOISE_TERMS = [
    "wednesday â€¢ 16 september 2026",
    "24 pages in 1 section",
    "volume xxxi number 30",
    "bennett, coleman & co. ltd.",
    "estd. 1838",
    "nk daily news mumbai whatsapp",
    "scan qr",
    "download app",
    "advertisement",
    "advertorial",
    "subscribe",
    "crossword",
    "campus spotlight",
]


# ============================================================
# TEXT HELPERS
# ============================================================

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


# ============================================================
# LOAD JSON
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# CONVERT RICH BLOCK
# ============================================================

def convert_block(block):

    return {
        "block_id": block["block"],
        "page": block["page"],

        "x0": float(block["x0"]),
        "y0": float(block["y0"]),
        "x1": float(block["x1"]),
        "y1": float(block["y1"]),

        "text": clean_text(
            block["text"]
        ),

        "line_count":
            block.get(
                "line_count",
                0
            ),

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

    smaller_width = min(
        width(a),
        width(b)
    )

    if smaller_width <= 0:
        return 0

    return overlap / smaller_width


def horizontal_distance(a, b):

    if a["x1"] < b["x0"]:

        return b["x0"] - a["x1"]

    if b["x1"] < a["x0"]:

        return a["x0"] - b["x1"]

    return 0


def vertical_gap(a, b):

    return b["y0"] - a["y1"]


def center_x(block):

    return (
        block["x0"]
        +
        block["x1"]
    ) / 2


# ============================================================
# HEADLINE SCORE
# ============================================================

def headline_score(block):

    text = block["text"]

    if not text:
        return -999

    if is_noise(text):
        return -999

    length = len(text)

    if length < 15:
        return -999

    if length > 180:
        return -999

    score = 0

    font = block["max_font_size"]
    bold = block["bold_ratio"]
    lines = block["line_count"]

    # --------------------------------------------------------
    # Font
    # --------------------------------------------------------

    if font >= 18:

        score += 6

    elif font >= 15:

        score += 5

    elif font >= 13:

        score += 4

    elif font >= 11:

        score += 2

    # --------------------------------------------------------
    # Bold
    # --------------------------------------------------------

    if bold >= 0.60:

        score += 3

    elif bold >= 0.30:

        score += 2

    elif bold > 0:

        score += 1

    # --------------------------------------------------------
    # Length
    # --------------------------------------------------------

    if 25 <= length <= 120:

        score += 2

    elif length <= 150:

        score += 1

    # --------------------------------------------------------
    # Lines
    # --------------------------------------------------------

    if lines <= 3:

        score += 2

    elif lines <= 5:

        score += 1

    # --------------------------------------------------------
    # Very short headlines are suspicious
    # --------------------------------------------------------

    if word_count(text) <= 2:

        score -= 2

    return score


# ============================================================
# FIND HEADLINES
# ============================================================

def find_headlines(
    page_blocks
):

    headlines = []

    for block in page_blocks:

        score = headline_score(
            block
        )

        if score >= MIN_HEADLINE_SCORE:

            headlines.append(
                {
                    **block,
                    "headline_score":
                        score
                }
            )

    headlines.sort(
        key=lambda x: (
            x["y0"],
            x["x0"]
        )
    )

    return headlines


# ============================================================
# REMOVE DUPLICATE / NESTED HEADLINES
# ============================================================

def remove_duplicate_headlines(
    headlines
):

    final = []

    for candidate in headlines:

        duplicate = False

        for existing in final:

            overlap = horizontal_overlap(
                candidate,
                existing
            )

            vertical_difference = abs(
                candidate["y0"]
                -
                existing["y0"]
            )

            if (
                overlap >= 0.50
                and
                vertical_difference <= 25
            ):

                duplicate = True

                if (
                    candidate["headline_score"]
                    >
                    existing["headline_score"]
                ):

                    final.remove(
                        existing
                    )

                    final.append(
                        candidate
                    )

                break

        if not duplicate:

            final.append(
                candidate
            )

    final.sort(
        key=lambda x: (
            x["y0"],
            x["x0"]
        )
    )

    return final


# ============================================================
# DETERMINE WHETHER A BLOCK IS BETWEEN TWO HEADLINES
# ============================================================

def nearest_headlines(
    block,
    headlines
):

    previous = None
    following = None

    for headline in headlines:

        if headline["y0"] <= block["y0"]:

            if (
                previous is None
                or
                headline["y0"]
                >
                previous["y0"]
            ):

                previous = headline

        elif (
            following is None
            or
            headline["y0"]
            <
            following["y0"]
        ):

            following = headline

    return previous, following


# ============================================================
# HORIZONTAL REGION RELATION
# ============================================================

def horizontal_relation(
    headline,
    block
):

    overlap = horizontal_overlap(
        headline,
        block
    )

    distance = horizontal_distance(
        headline,
        block
    )

    # Directly under the headline
    if overlap >= 0.50:

        return "DIRECT"

    # Slightly shifted continuation
    if overlap >= 0.20:

        return "NEAR"

    # Adjacent physical newspaper column
    if distance <= MAX_HORIZONTAL_DISTANCE:

        return "ADJACENT"

    return "FAR"


# ============================================================
# BODY BLOCK SCORE
# ============================================================

def article_block_score(
    headline,
    block,
    previous_article_blocks,
    next_headline
):

    text = block["text"]

    if not text:
        return -999

    if is_noise(text):
        return -999

    if len(text) < MIN_BODY_LENGTH:
        return -999

    # Never include another headline
    if (
        block["block_id"]
        ==
        (
            next_headline["block_id"]
            if next_headline
            else False
        )
    ):

        return -999

    score = 0

    # --------------------------------------------------------
    # Position relative to headline
    # --------------------------------------------------------

    if block["y0"] < headline["y1"]:

        return -999

    vertical_distance = (
        block["y0"]
        -
        headline["y1"]
    )

    if vertical_distance <= 40:

        score += 5

    elif vertical_distance <= 100:

        score += 4

    elif vertical_distance <= 200:

        score += 3

    elif vertical_distance <= MAX_VERTICAL_DISTANCE:

        score += 1

    else:

        return -999

    # --------------------------------------------------------
    # Horizontal relation
    # --------------------------------------------------------

    relation = horizontal_relation(
        headline,
        block
    )

    if relation == "DIRECT":

        score += 6

    elif relation == "NEAR":

        score += 4

    elif relation == "ADJACENT":

        score += 2

    else:

        score -= 3

    # --------------------------------------------------------
    # Body font should normally be smaller
    # --------------------------------------------------------

    if (
        block["min_font_size"]
        <=
        headline["min_font_size"]
    ):

        score += 2

    # --------------------------------------------------------
    # Text length
    # --------------------------------------------------------

    if len(text) >= 100:

        score += 2

    elif len(text) >= 50:

        score += 1

    # --------------------------------------------------------
    # Continuation from an already accepted block
    # --------------------------------------------------------

    if previous_article_blocks:

        best_previous_score = 0

        for previous in previous_article_blocks:

            if (
                block["y0"]
                <
                previous["y0"]
            ):

                continue

            gap = (
                block["y0"]
                -
                previous["y1"]
            )

            if gap < 0:

                continue

            if gap > 180:

                continue

            overlap = horizontal_overlap(
                previous,
                block
            )

            distance = horizontal_distance(
                previous,
                block
            )

            local_score = 0

            if overlap >= 0.40:

                local_score += 5

            elif overlap >= 0.15:

                local_score += 3

            elif distance <= 180:

                local_score += 2

            if gap <= 50:

                local_score += 3

            elif gap <= 100:

                local_score += 2

            best_previous_score = max(
                best_previous_score,
                local_score
            )

        score += best_previous_score

    return score


# ============================================================
# DETECT SPECIAL BLOCKS
# ============================================================

def detect_role(
    block,
    headline
):

    text = block["text"]

    lower = text.lower()

    # --------------------------------------------------------
    # Byline
    # --------------------------------------------------------

    if (
        len(text) < 120
        and
        (
            lower.startswith("by ")
            or
            "new delhi," in lower
            or
            "mumbai," in lower
        )
    ):

        return "BYLINE"

    # --------------------------------------------------------
    # Subheadline
    # --------------------------------------------------------

    if (
        block["min_font_size"]
        >= 9
        and
        len(text) <= 180
        and
        block["line_count"] <= 3
    ):

        gap = (
            block["y0"]
            -
            headline["y1"]
        )

        if 0 <= gap <= 100:

            return "SUBHEAD"

    # --------------------------------------------------------
    # Fact box / short information
    # --------------------------------------------------------

    if (
        len(text) < 90
        and
        block["line_count"] <= 3
    ):

        return "RELATED"

    return "BODY"


# ============================================================
# BUILD ONE ARTICLE
# ============================================================

def build_article(
    headline,
    accepted_blocks
):

    all_blocks = [
        headline
    ] + accepted_blocks

    all_blocks.sort(
        key=lambda b: (
            b["y0"],
            b["x0"]
        )
    )

    body = []
    subheads = []
    bylines = []
    related = []

    for block in accepted_blocks:

        role = detect_role(
            block,
            headline
        )

        if role == "BYLINE":

            bylines.append(
                block
            )

        elif role == "SUBHEAD":

            subheads.append(
                block
            )

        elif role == "RELATED":

            related.append(
                block
            )

        else:

            body.append(
                block
            )

    full_text_parts = []

    for block in all_blocks:

        full_text_parts.append(
            block["text"]
        )

    return {

        "page":
            headline["page"],

        "headline_block":
            headline["block_id"],

        "headline":
            headline["text"],

        "headline_score":
            headline["headline_score"],

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
            "\n\n".join(
                b["text"]
                for b in body
            ),

        "related_blocks":
            [
                b["text"]
                for b in related
            ],

        "full_article_text":
            "\n\n".join(
                full_text_parts
            ),

        "block_count":
            len(all_blocks),

        "body_block_count":
            len(body),

        "needs_review":
            len(body) == 0,

        "blocks":
            [
                {
                    "block_id":
                        b["block_id"],

                    "role":
                        (
                            "HEADLINE"
                            if
                            b["block_id"]
                            ==
                            headline["block_id"]
                            else
                            detect_role(
                                b,
                                headline
                            )
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
# ASSIGN BLOCKS TO HEADLINES
# ============================================================

def group_page(
    page_blocks
):

    # --------------------------------------------------------
    # 1. Find headline anchors
    # --------------------------------------------------------

    headlines = find_headlines(
        page_blocks
    )

    headlines = remove_duplicate_headlines(
        headlines
    )

    if not headlines:

        diagnostics = {
            "headline_count": 0,
            "article_count": 0,
            "headlines": []
        }

        return (
            [],
            diagnostics
        )

    # --------------------------------------------------------
    # 2. Every headline starts an article region
    # --------------------------------------------------------

    articles = []

    assigned_blocks = set()

    # Headline blocks themselves are reserved.
    for headline in headlines:

        assigned_blocks.add(
            headline["block_id"]
        )

    # --------------------------------------------------------
    # 3. Process each headline independently
    # --------------------------------------------------------

    for index, headline in enumerate(
        headlines
    ):

        # ----------------------------------------------------
        # Next headline
        # ----------------------------------------------------

        next_headline = None

        if index + 1 < len(headlines):

            next_headline = headlines[
                index + 1
            ]

        candidate_blocks = []

        # ----------------------------------------------------
        # Examine every non-headline block
        # ----------------------------------------------------

        for block in page_blocks:

            if (
                block["block_id"]
                ==
                headline["block_id"]
            ):

                continue

            # Already assigned to another article.
            if (
                block["block_id"]
                in
                assigned_blocks
            ):

                continue

            score = article_block_score(
                headline,
                block,
                candidate_blocks,
                next_headline
            )

            if score < 9:

                continue

            candidate_blocks.append(
                block
            )

            if (
                len(candidate_blocks)
                >=
                MAX_BLOCKS - 1
            ):

                break

        # ----------------------------------------------------
        # Sort selected blocks
        # ----------------------------------------------------

        candidate_blocks.sort(
            key=lambda b: (
                b["y0"],
                b["x0"]
            )
        )

        # ----------------------------------------------------
        # Keep only reasonable continuity
        # ----------------------------------------------------

        final_blocks = []

        previous = headline

        for block in candidate_blocks:

            gap = (
                block["y0"]
                -
                previous["y1"]
            )

            overlap = horizontal_overlap(
                previous,
                block
            )

            distance = horizontal_distance(
                previous,
                block
            )

            # Direct continuation
            if (
                gap <= 120
                and
                (
                    overlap >= 0.15
                    or
                    distance <= 220
                )
            ):

                final_blocks.append(
                    block
                )

                previous = block

        # ----------------------------------------------------
        # Build article
        # ----------------------------------------------------

        article = build_article(
            headline,
            final_blocks
        )

        articles.append(
            article
        )

        # ----------------------------------------------------
        # Reserve blocks
        # ----------------------------------------------------

        for block in final_blocks:

            assigned_blocks.add(
                block["block_id"]
            )

    # --------------------------------------------------------
    # Diagnostics
    # --------------------------------------------------------

    diagnostics = {

        "headline_count":
            len(headlines),

        "article_count":
            len(articles),

        "headlines":
            [
                {
                    "block":
                        h["block_id"],

                    "score":
                        h["headline_score"],

                    "text":
                        h["text"],

                    "x0":
                        h["x0"],

                    "y0":
                        h["y0"]
                }

                for h in headlines
            ]
    }

    return (
        articles,
        diagnostics
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
        "=" * 100
    )

    print(
        newspaper_name
    )

    print(
        "=" * 100
    )

    raw = load_json(
        rich_file
    )

    blocks = [
        convert_block(
            block
        )
        for block in raw
    ]

    pages = defaultdict(list)

    for block in blocks:

        pages[
            block["page"]
        ].append(
            block
        )

    # ========================================================
    # PRODUCTION MODE:
    # PROCESS EVERY PAGE
    # ========================================================

    pages_to_process = sorted(
        pages.keys()
    )

    output_pages = []

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

        articles, diagnostics = group_page(
            page_blocks
        )

        # Safety check.
        # group_page() must return:
        #     articles = list
        #     diagnostics = dictionary
        if not isinstance(
            articles,
            list
        ):

            raise TypeError(
                f"group_page() returned invalid "
                f"articles object on page {page_number}: "
                f"{type(articles).__name__}"
            )

        if not isinstance(
            diagnostics,
            dict
        ):

            raise TypeError(
                f"group_page() returned invalid "
                f"diagnostics object on page {page_number}: "
                f"{type(diagnostics).__name__}"
            )

        print()
        print(
            f"PAGE {page_number}"
        )

        print(
            f"Total blocks: "
            f"{len(page_blocks)}"
        )

        print(
            f"Headline candidates: "
            f"{diagnostics.get('headline_count', 0)}"
        )

        print(
            f"Article groups: "
            f"{diagnostics.get('article_count', 0)}"
        )

        print(
            "-" * 100
        )

        for i, article in enumerate(
            articles,
            start=1
        ):

            block_ids = [
                b["block_id"]
                for b in article["blocks"]
            ]

            print(
                f"[{i}] "
                f"B{article['headline_block']} "
                f"| "
                f"{article['headline']}"
            )

            print(
                f"    blocks: "
                f"{block_ids}"
            )

            print(
                f"    body blocks: "
                f"{article['body_block_count']}"
            )

            print(
                f"    review: "
                f"{article['needs_review']}"
            )

        output_pages.append(
            {
                "page":
                    page_number,

                "total_blocks":
                    len(page_blocks),

                "diagnostics":
                    diagnostics,

                "articles":
                    articles
            }
        )

    # ========================================================
    # SAVE
    # ========================================================

    output_file = (
        OUTPUT_DIR
        /
        f"{newspaper_name}"
        "_grouped_v4.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output_pages,
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
            "ERROR: No rich-block files found."
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
        "=" * 100
    )

    print(
        "GENERAL ARTICLE GROUPING V4 COMPLETE"
    )

    print(
        "=" * 100
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()