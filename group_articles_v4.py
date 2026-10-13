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
# GEOMETRY
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


def vertical_gap(block1, block2):

    if block2["y0"] >= block1["y1"]:
        return block2["y0"] - block1["y1"]

    return 9999


# ---------------------------------------------------------
# FIND BLOCK
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
# POSSIBLE HEADLINE
# ---------------------------------------------------------

def is_headline(block, original_headline):

    if block["block"] == original_headline["block"]:
        return False

    text = block["text"].strip()

    if not text:
        return False

    font_size = block.get(
        "max_font_size",
        0
    )

    # Large font
    if font_size >= 18:
        return True

    # Medium font + short text
    if (
        font_size >= 15
        and len(text) < 150
        and len(text.split()) >= 4
    ):
        return True

    return False


# ---------------------------------------------------------
# BODY BLOCK
# ---------------------------------------------------------

def is_body(block):

    text = block["text"].strip()

    if not text:
        return False

    font_size = block.get(
        "max_font_size",
        0
    )

    if font_size >= 18:
        return False

    if len(text) < 20:
        return False

    return True


# ---------------------------------------------------------
# AGRICULTURE RELEVANCE
# ---------------------------------------------------------

def is_relevant(block):

    relevance = block.get(
        "agriculture_relevance",
        "LOW"
    )

    return relevance in [
        "HIGH",
        "POSSIBLE"
    ]


# ---------------------------------------------------------
# NARROW ARTICLE
# ---------------------------------------------------------

def group_narrow_article(
    page_blocks,
    headline
):

    story = [
        headline
    ]

    used = {
        headline["block"]
    }

    current = headline

    while True:

        candidates = []

        for block in page_blocks:

            if block["block"] in used:
                continue

            if block["y0"] < current["y1"]:
                continue

            gap = vertical_gap(
                current,
                block
            )

            if gap > 180:
                continue

            if is_headline(
                block,
                headline
            ):
                continue

            if not is_body(block):
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

                candidates.append(
                    (
                        gap,
                        0,
                        block
                    )
                )

            # Very close adjacent column
            elif distance <= 15:

                candidates.append(
                    (
                        gap,
                        1,
                        block
                    )
                )

        if not candidates:
            break

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1]
            )
        )

        next_block = candidates[0][2]

        story.append(
            next_block
        )

        used.add(
            next_block["block"]
        )

        current = next_block

    return story


# ---------------------------------------------------------
# WIDE MULTI-COLUMN ARTICLE
# ---------------------------------------------------------

def group_wide_article(
    page_blocks,
    headline
):

    story = [
        headline
    ]

    used = {
        headline["block"]
    }

    # -----------------------------------------------------
    # First identify relevant body blocks.
    # -----------------------------------------------------

    candidates = []

    for block in page_blocks:

        if block["block"] in used:
            continue

        if block["y0"] < headline["y1"]:
            continue

        # Search only below the headline.
        if block["y0"] > headline["y1"] + 400:
            continue

        if not is_body(block):
            continue

        if not is_relevant(block):
            continue

        candidates.append(block)

    candidates.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    # -----------------------------------------------------
    # Add relevant blocks while preventing contamination
    # from another obvious headline.
    # -----------------------------------------------------

    for block in candidates:

        # If this is clearly another headline,
        # do not include it or anything belonging
        # to that story.
        if is_headline(
            block,
            headline
        ):
            continue

        # Find nearby story blocks.
        nearest_gap = 9999

        for previous in story:

            gap = vertical_gap(
                previous,
                block
            )

            if gap < nearest_gap:
                nearest_gap = gap

        # Body should remain reasonably connected
        # to the existing story.
        if nearest_gap <= 150:

            story.append(
                block
            )

            used.add(
                block["block"]
            )

    story.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    return story


# ---------------------------------------------------------
# GROUP ARTICLE
# ---------------------------------------------------------

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

    # Narrow headline
    if headline["width"] < 300:

        return group_narrow_article(
            page_blocks,
            headline
        )

    # Wide headline
    return group_wide_article(
        page_blocks,
        headline
    )


# ---------------------------------------------------------
# PROCESS FILES
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

        article_candidates = json.load(file)

    with open(
        merged_file,
        "r",
        encoding="utf-8"
    ) as file:

        blocks = json.load(file)

    grouped_articles = []

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
    "ARTICLE GROUPING V4 COMPLETE"
)
print("=" * 100)