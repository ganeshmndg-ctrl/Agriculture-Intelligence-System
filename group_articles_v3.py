import json
from pathlib import Path


merged_folder = Path("data/merged_blocks")
articles_folder = Path("data/articles")
output_folder = Path("data/grouped_articles")

output_folder.mkdir(
    parents=True,
    exist_ok=True
)


# ---------------------------------------------------------
# GEOMETRY FUNCTIONS
# ---------------------------------------------------------

def horizontal_overlap(block1, block2):

    left = max(
        block1["x0"],
        block2["x0"]
    )

    right = min(
        block1["x1"],
        block2["x1"]
    )

    return max(0, right - left)


def horizontal_distance(block1, block2):

    if block1["x1"] < block2["x0"]:
        return block2["x0"] - block1["x1"]

    if block2["x1"] < block1["x0"]:
        return block1["x0"] - block2["x1"]

    return 0


def vertical_gap(block1, block2):

    if block2["y0"] >= block1["y1"]:
        return block2["y0"] - block1["y1"]

    return 9999


# ---------------------------------------------------------
# FIND A SPECIFIC BLOCK
# ---------------------------------------------------------

def find_block(blocks, page, block_number):

    for block in blocks:

        if (
            block["page"] == page
            and block["block"] == block_number
        ):
            return block

    return None


# ---------------------------------------------------------
# IDENTIFY POSSIBLE NEW HEADLINES
# ---------------------------------------------------------

def is_large_headline(block, original_headline):

    if block["block"] == original_headline["block"]:
        return False

    font_size = block.get("max_font_size", 0)

    text = block["text"].strip()

    if not text:
        return False

    # Very large text is likely another headline
    if font_size >= 20:
        return True

    # Medium-sized short text may also be a headline
    if (
        font_size >= 15
        and len(text) < 150
        and len(text.split()) >= 4
    ):
        return True

    return False


# ---------------------------------------------------------
# IDENTIFY BODY-LIKE BLOCKS
# ---------------------------------------------------------

def is_body_like(block):

    font_size = block.get("max_font_size", 0)

    text = block["text"].strip()

    if not text:
        return False

    # Large text is probably a heading
    if font_size >= 20:
        return False

    # Very short fragments are usually labels,
    # numbers, page furniture, etc.
    if len(text) < 20:
        return False

    return True


# ---------------------------------------------------------
# FIND THE NEXT BLOCK IN THE SAME PHYSICAL REGION
# ---------------------------------------------------------

def find_next_same_region(current, candidates):

    possible = []

    for block in candidates:

        if block["block"] == current["block"]:
            continue

        gap = vertical_gap(
            current,
            block
        )

        if gap == 9999:
            continue

        # Don't jump too far vertically
        if gap > 180:
            continue

        overlap = horizontal_overlap(
            current,
            block
        )

        distance = horizontal_distance(
            current,
            block
        )

        # Same column
        if overlap > 0:

            possible.append(
                (
                    gap,
                    0,
                    block
                )
            )

        # Very close adjacent column
        elif distance <= 15:

            possible.append(
                (
                    gap,
                    1,
                    block
                )
            )

    if not possible:
        return None

    possible.sort(
        key=lambda item: (
            item[0],
            item[1]
        )
    )

    return possible[0][2]


# ---------------------------------------------------------
# GROUP ONE ARTICLE
# ---------------------------------------------------------

def group_story(blocks, headline):

    page = headline["page"]

    page_blocks = [
        block
        for block in blocks
        if block["page"] == page
    ]

    story_blocks = [
        headline
    ]

    used = {
        headline["block"]
    }

    current = headline

    # -----------------------------------------------------
    # STAGE 1
    # Follow the same physical column/region.
    # -----------------------------------------------------

    while True:

        candidates = [
            block
            for block in page_blocks
            if block["block"] not in used
            and block["y0"] >= current["y1"]
        ]

        next_block = find_next_same_region(
            current,
            candidates
        )

        if next_block is None:
            break

        # Stop if we encounter another headline
        if is_large_headline(
            next_block,
            headline
        ):
            break

        # Ignore tiny fragments
        if not is_body_like(next_block):

            used.add(
                next_block["block"]
            )

            continue

        story_blocks.append(
            next_block
        )

        used.add(
            next_block["block"]
        )

        current = next_block

    # -----------------------------------------------------
    # STAGE 2
    # Handle wide multi-column stories.
    #
    # Example:
    # ET drought article
    # ET rice/ethanol article
    # -----------------------------------------------------

    headline_width = headline["width"]

    if headline_width >= 300:

        region_left = headline["x0"]
        region_right = headline["x1"]

        region_candidates = []

        for block in page_blocks:

            if block["block"] in used:
                continue

            if block["y0"] < headline["y1"]:
                continue

            # Don't search too far below headline
            if block["y0"] > headline["y1"] + 450:
                continue

            # Check whether block lies inside
            # the headline's horizontal region.
            overlap = max(
                0,
                min(
                    region_right,
                    block["x1"]
                )
                -
                max(
                    region_left,
                    block["x0"]
                )
            )

            if overlap <= 0:
                continue

            if not is_body_like(block):
                continue

            if is_large_headline(
                block,
                headline
            ):
                continue

            region_candidates.append(
                block
            )

        region_candidates.sort(
            key=lambda block: (
                block["y0"],
                block["x0"]
            )
        )

        # Add blocks that remain reasonably
        # connected to the article.
        for block in region_candidates:

            nearest_gap = 9999

            for previous in story_blocks:

                gap = vertical_gap(
                    previous,
                    block
                )

                if gap < nearest_gap:
                    nearest_gap = gap

            if nearest_gap <= 180:

                story_blocks.append(
                    block
                )

                used.add(
                    block["block"]
                )

    # -----------------------------------------------------
    # FINAL ORDER
    # -----------------------------------------------------

    story_blocks.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    return story_blocks


# ---------------------------------------------------------
# PROCESS ARTICLE CANDIDATE FILES
# ---------------------------------------------------------

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

    # Find corresponding merged blocks file
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

    # Load article candidates
    with open(
        article_file,
        "r",
        encoding="utf-8"
    ) as file:

        article_candidates = json.load(file)

    # Load merged blocks
    with open(
        merged_file,
        "r",
        encoding="utf-8"
    ) as file:

        blocks = json.load(file)

    grouped_articles = []

    # -----------------------------------------------------
    # PROCESS EACH ARTICLE CANDIDATE
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

        story_blocks = group_story(
            blocks,
            headline
        )

        article_text = []

        for block in story_blocks:

            article_text.append(
                block["text"]
            )

        article = {

            "newspaper":
                article_file.name.replace(
                    "_blocks_articles.json",
                    ""
                ),

            "page":
                headline["page"],

            "headline":
                headline["text"],

            "headline_block":
                headline["block"],

            "story_block_count":
                len(story_blocks),

            "blocks":
                story_blocks,

            "article_text":
                "\n\n".join(
                    article_text
                )
        }

        grouped_articles.append(
            article
        )

        # -------------------------------------------------
        # PRINT RESULT
        # -------------------------------------------------

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
    # SAVE OUTPUT
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
    "ARTICLE GROUPING V3 COMPLETE"
)
print("=" * 100)