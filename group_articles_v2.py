import json
from pathlib import Path


merged_folder = Path("data/merged_blocks")
articles_folder = Path("data/articles")
output_folder = Path("data/grouped_articles")

output_folder.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# BASIC GEOMETRY FUNCTIONS
# =========================================================

def horizontal_overlap(block1, block2):

    left = max(
        block1["x0"],
        block2["x0"]
    )

    right = min(
        block1["x1"],
        block2["x1"]
    )

    return max(
        0,
        right - left
    )


def horizontal_distance(block1, block2):

    if block1["x1"] < block2["x0"]:
        return block2["x0"] - block1["x1"]

    if block2["x1"] < block1["x0"]:
        return block1["x0"] - block2["x1"]

    return 0


def vertical_gap(headline, block):

    if block["y0"] >= headline["y1"]:
        return block["y0"] - headline["y1"]

    return 9999


# =========================================================
# DETECT POSSIBLE NEW HEADLINES
# =========================================================

def is_new_headline(block, original_headline):

    if block["block"] == original_headline["block"]:
        return False

    font_size = block.get(
        "max_font_size",
        0
    )

    text = block["text"].strip()

    if not text:
        return False

    # Large font is a strong signal
    if font_size >= 18:
        return True

    # Medium font + substantial text
    if (
        font_size >= 13
        and len(text) < 180
        and len(text.split()) >= 4
    ):
        return True

    return False


# =========================================================
# SCORE A BLOCK AS PART OF THE ARTICLE
# =========================================================

def article_block_score(
    headline,
    block,
    story_blocks
):

    score = 0

    gap = vertical_gap(
        headline,
        block
    )

    if gap == 9999:
        return -999

    overlap = horizontal_overlap(
        headline,
        block
    )

    distance = horizontal_distance(
        headline,
        block
    )

    # -----------------------------------------------------
    # 1. Vertical proximity
    # -----------------------------------------------------

    if gap <= 30:
        score += 5

    elif gap <= 80:
        score += 4

    elif gap <= 150:
        score += 3

    elif gap <= 250:
        score += 2

    elif gap <= 400:
        score += 1

    else:
        return -999

    # -----------------------------------------------------
    # 2. Horizontal relationship
    # -----------------------------------------------------

    if overlap > 0:
        score += 4

    elif distance < 20:
        score += 3

    elif distance < 60:
        score += 2

    elif distance < 120:
        score += 1

    # -----------------------------------------------------
    # 3. Agriculture relevance
    # -----------------------------------------------------

    relevance = block.get(
        "agriculture_relevance",
        "LOW"
    )

    if relevance == "HIGH":
        score += 3

    elif relevance == "POSSIBLE":
        score += 1

    # -----------------------------------------------------
    # 4. Font size
    #
    # Body text normally has smaller font.
    # Large font may indicate another headline.
    # -----------------------------------------------------

    font_size = block.get(
        "max_font_size",
        0
    )

    if font_size >= 18:
        score -= 6

    elif font_size >= 13:
        score -= 2

    # -----------------------------------------------------
    # 5. Compare with previously accepted story blocks
    #
    # This allows the article to move into adjacent
    # newspaper columns.
    # -----------------------------------------------------

    if story_blocks:

        best_story_relationship = 0

        for previous in story_blocks:

            overlap_with_previous = horizontal_overlap(
                previous,
                block
            )

            distance_from_previous = horizontal_distance(
                previous,
                block
            )

            previous_y_gap = 0

            if block["y0"] >= previous["y1"]:
                previous_y_gap = (
                    block["y0"] - previous["y1"]
                )

            relationship = 0

            if overlap_with_previous > 0:
                relationship += 3

            elif distance_from_previous < 20:
                relationship += 2

            elif distance_from_previous < 60:
                relationship += 1

            if previous_y_gap < 80:
                relationship += 2

            elif previous_y_gap < 150:
                relationship += 1

            best_story_relationship = max(
                best_story_relationship,
                relationship
            )

        score += best_story_relationship

    return score


# =========================================================
# FIND HEADLINE BLOCK
# =========================================================

def find_block(
    blocks,
    page,
    block_number
):

    for block in blocks:

        if (
            block["page"] == page
            and block["block"] == block_number
        ):
            return block

    return None


# =========================================================
# GROUP ONE ARTICLE
# =========================================================

def group_article(
    blocks,
    headline
):

    page = headline["page"]

    page_blocks = [
        block
        for block in blocks
        if block["page"] == page
    ]

    story_blocks = [
        headline
    ]

    # -----------------------------------------------------
    # Sort blocks physically
    # -----------------------------------------------------

    remaining_blocks = [
        block
        for block in page_blocks
        if block["block"] != headline["block"]
    ]

    remaining_blocks.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    # -----------------------------------------------------
    # Examine blocks one by one
    # -----------------------------------------------------

    for block in remaining_blocks:

        # Nothing above the headline
        if block["y0"] < headline["y1"]:
            continue

        # Ignore blocks very far away
        if (
            block["y0"] -
            headline["y1"]
        ) > 500:
            continue

        # -------------------------------------------------
        # Stop at a strong new headline
        # -------------------------------------------------

        if is_new_headline(
            block,
            headline
        ):

            # If it is very close to headline,
            # definitely treat as another story.
            if (
                block["y0"] -
                headline["y1"]
            ) < 100:
                continue

        # -------------------------------------------------
        # Score block
        # -------------------------------------------------

        score = article_block_score(
            headline,
            block,
            story_blocks
        )

        # -------------------------------------------------
        # Accept only reasonably strong candidates
        # -------------------------------------------------

        if score >= 7:

            story_blocks.append(
                block
            )

    # -----------------------------------------------------
    # Remove accidental unrelated blocks
    #
    # Sort story physically.
    # -----------------------------------------------------

    story_blocks.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    return story_blocks


# =========================================================
# PROCESS ALL NEWSPAPERS
# =========================================================

for article_file in articles_folder.glob(
    "*_articles.json"
):

    print()
    print("=" * 100)
    print(
        "PROCESSING:",
        article_file.name
    )
    print("=" * 100)

    merged_file = (
        merged_folder /
        article_file.name.replace(
            "_blocks_articles.json",
            "_blocks.json"
        )
    )

    if not merged_file.exists():

        print(
            "Merged file not found:",
            merged_file
        )

        continue

    with open(
        article_file,
        "r",
        encoding="utf-8"
    ) as file:

        article_candidates = json.load(
            file
        )

    with open(
        merged_file,
        "r",
        encoding="utf-8"
    ) as file:

        blocks = json.load(
            file
        )

    grouped_articles = []

    # -----------------------------------------------------
    # Group every detected headline
    # -----------------------------------------------------

    for article_number, candidate in enumerate(
        article_candidates,
        start=1
    ):

        headline = find_block(
            blocks,
            candidate["page"],
            candidate["headline_block"]
        )

        if headline is None:
            continue

        story_blocks = group_article(
            blocks,
            headline
        )

        article_text = []

        for block in story_blocks:

            article_text.append(
                block["text"]
            )

        article = {

            "newspaper": article_file.name.replace(
                "_blocks_articles.json",
                ""
            ),

            "page": headline["page"],

            "headline": headline["text"],

            "headline_block": headline["block"],

            "story_block_count": len(
                story_blocks
            ),

            "blocks": story_blocks,

            "article_text": "\n\n".join(
                article_text
            )
        }

        grouped_articles.append(
            article
        )

        print()
        print(
            f"ARTICLE {article_number}: "
            f"{headline['text']}"
        )

        print(
            "Story blocks:",
            len(story_blocks)
        )

        print(
            "Block numbers:",
            [
                block["block"]
                for block in story_blocks
            ]
        )

    # -----------------------------------------------------
    # Save
    # -----------------------------------------------------

    output_file = (
        output_folder /
        article_file.name.replace(
            "_articles.json",
            "_grouped.json"
        )
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            grouped_articles,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print(
        "Saved:",
        output_file
    )


print()
print("=" * 100)
print(
    "ARTICLE GROUPING COMPLETE"
)
print("=" * 100)