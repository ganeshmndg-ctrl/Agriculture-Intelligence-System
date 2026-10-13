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
# GEOMETRY FUNCTIONS
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


# =========================================================
# FIND BLOCK
# =========================================================

def find_block(blocks, page, block_number):

    for block in blocks:

        if (
            block["page"] == page
            and block["block"] == block_number
        ):
            return block

    return None


# =========================================================
# HEADLINE DETECTION
# =========================================================

def looks_like_headline(block, original_headline):

    if block["block"] == original_headline["block"]:
        return False

    text = block["text"].strip()

    if not text:
        return False

    font_size = block.get(
        "max_font_size",
        0
    )

    # Very large text
    if font_size >= 20:
        return True

    # Medium headline
    if (
        font_size >= 15
        and len(text) < 150
        and len(text.split()) >= 4
    ):
        return True

    return False


# =========================================================
# BODY DETECTION
# =========================================================

def is_body(block):

    text = block["text"].strip()

    if not text:
        return False

    font_size = block.get(
        "max_font_size",
        0
    )

    if font_size >= 20:
        return False

    if len(text) < 20:
        return False

    return True


# =========================================================
# RELEVANCE
# =========================================================

def is_agri_relevant(block):

    return block.get(
        "agriculture_relevance",
        "LOW"
    ) in [
        "HIGH",
        "POSSIBLE"
    ]


# =========================================================
# GET PAGE BLOCKS
# =========================================================

def get_page_blocks(blocks, page):

    page_blocks = [
        block
        for block in blocks
        if block["page"] == page
    ]

    return sorted(
        page_blocks,
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )


# =========================================================
# NARROW STORY
# =========================================================

def group_narrow_story(
    page_blocks,
    headline
):

    story = [
        headline
    ]

    used = {
        headline["block"]
    }

    # FIXED horizontal region.
    # We do NOT allow the region to move
    # as we add more blocks.

    region_left = headline["x0"] - 10
    region_right = headline["x1"] + 10

    candidates = []

    for block in page_blocks:

        if block["block"] in used:
            continue

        if block["y0"] < headline["y1"]:
            continue

        if block["y0"] > headline["y1"] + 500:
            continue

        if not is_body(block):
            continue

        # Block must remain inside
        # the headline's physical region.

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

        candidates.append(block)

    candidates.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    # -----------------------------------------------------
    # Add blocks until a new story begins.
    # -----------------------------------------------------

    last_y = headline["y1"]

    for block in candidates:

        gap = block["y0"] - last_y

        # Large unexplained gap = probably end of story
        if gap > 160:
            break

        # Look for a headline between the
        # previous story block and this block.
        barrier = False

        for other in page_blocks:

            if other["block"] in used:
                continue

            if other["y0"] <= last_y:
                continue

            if other["y0"] >= block["y0"]:
                continue

            if looks_like_headline(
                other,
                headline
            ):
                barrier = True
                break

        if barrier:
            break

        story.append(block)

        used.add(
            block["block"]
        )

        last_y = block["y1"]

    return story


# =========================================================
# WIDE MULTI-COLUMN STORY
# =========================================================

def group_wide_story(
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
    # FIXED horizontal region from headline
    # -----------------------------------------------------

    region_left = headline["x0"]
    region_right = headline["x1"]

    candidates = []

    for block in page_blocks:

        if block["block"] in used:
            continue

        if block["y0"] < headline["y1"]:
            continue

        if block["y0"] > headline["y1"] + 450:
            continue

        if not is_body(block):
            continue

        # Must be relevant to agriculture.
        if not is_agri_relevant(block):
            continue

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

        candidates.append(block)

    candidates.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    # -----------------------------------------------------
    # Add blocks while checking for
    # a new story boundary.
    # -----------------------------------------------------

    for block in candidates:

        barrier = False

        for other in page_blocks:

            if other["block"] in used:
                continue

            # Headline must occur between the
            # last known story area and this block.

            if other["y0"] >= block["y0"]:
                continue

            if other["y0"] <= headline["y1"]:
                continue

            if not looks_like_headline(
                other,
                headline
            ):
                continue

            # Check whether this looks like a
            # separate narrow story rather than
            # an internal label.

            other_width = other["width"]

            if other_width < 250:

                barrier = True
                break

        if barrier:
            continue

        # Connect block to existing story.
        nearest_gap = 9999

        for previous in story:

            gap = vertical_gap(
                previous,
                block
            )

            if gap < nearest_gap:
                nearest_gap = gap

        if nearest_gap <= 180:

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


# =========================================================
# GROUP ARTICLE
# =========================================================

def group_article(
    blocks,
    headline
):

    page_blocks = get_page_blocks(
        blocks,
        headline["page"]
    )

    # Very small headline:
    # don't aggressively reconstruct.
    if headline["width"] < 180:

        story = group_narrow_story(
            page_blocks,
            headline
        )

        # If no convincing body was found,
        # retain headline only.
        relevant_body = [
            block
            for block in story
            if block["block"] != headline["block"]
            and is_agri_relevant(block)
        ]

        if not relevant_body:

            return [
                headline
            ]

        return story

    # Normal narrow article
    if headline["width"] < 300:

        return group_narrow_story(
            page_blocks,
            headline
        )

    # Wide multi-column article
    return group_wide_story(
        page_blocks,
        headline
    )


# =========================================================
# PROCESS FILES
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
    "ARTICLE GROUPING V5 COMPLETE"
)
print("=" * 100)