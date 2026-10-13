import json
from pathlib import Path


merged_folder = Path("data/merged_blocks")
articles_folder = Path("data/articles")


def horizontal_overlap(block1, block2):
    left = max(block1["x0"], block2["x0"])
    right = min(block1["x1"], block2["x1"])

    return max(0, right - left)


def vertical_gap(headline, block):
    if block["y0"] >= headline["y1"]:
        return block["y0"] - headline["y1"]

    return 9999


def is_below(headline, block):
    return block["y0"] >= headline["y1"]


def score_nearby_block(headline, block):

    if not is_below(headline, block):
        return -999

    gap = vertical_gap(headline, block)
    overlap = horizontal_overlap(headline, block)

    headline_center = (headline["x0"] + headline["x1"]) / 2
    block_center = (block["x0"] + block["x1"]) / 2

    center_difference = abs(
        headline_center - block_center
    )

    score = 0

    # Vertical distance
    if gap < 30:
        score += 5
    elif gap < 80:
        score += 4
    elif gap < 150:
        score += 3
    elif gap < 250:
        score += 2
    elif gap < 400:
        score += 1

    # Horizontal overlap
    if overlap > 0:
        score += 3

    # Horizontal centre proximity
    if center_difference < 50:
        score += 3
    elif center_difference < 120:
        score += 2
    elif center_difference < 250:
        score += 1

    # Agriculture relevance
    if block.get("agriculture_relevance") == "HIGH":
        score += 2
    elif block.get("agriculture_relevance") == "POSSIBLE":
        score += 1

    return score


# =========================================================
# PROCESS ARTICLE CANDIDATE FILES
# =========================================================

for article_file in articles_folder.glob("*_articles.json"):

    print()
    print("=" * 110)
    print("ARTICLE DIAGNOSTIC")
    print("=" * 110)
    print("FILE:", article_file.name)
    print("=" * 110)

    # -----------------------------------------------------
    # Load article candidates
    # -----------------------------------------------------

    with open(article_file, "r", encoding="utf-8") as file:
        articles = json.load(file)

    if not articles:
        print("No article candidates found.")
        continue

    # -----------------------------------------------------
    # Find corresponding merged block file
    # -----------------------------------------------------

    merged_file = (
        merged_folder /
        article_file.name.replace(
            "_blocks_articles.json",
            "_blocks.json"
        )
    )

    if not merged_file.exists():

        print(
            "Merged block file not found:",
            merged_file
        )

        continue

    # -----------------------------------------------------
    # Load merged blocks
    # -----------------------------------------------------

    with open(merged_file, "r", encoding="utf-8") as file:
        blocks = json.load(file)

    # =====================================================
    # INSPECT EACH ARTICLE CANDIDATE
    # =====================================================

    for article_number, article in enumerate(
        articles,
        start=1
    ):

        page = article["page"]
        headline_block_number = article["headline_block"]

        headline = None

        # -------------------------------------------------
        # Find headline block
        # -------------------------------------------------

        for block in blocks:

            if (
                block["page"] == page
                and block["block"] == headline_block_number
            ):

                headline = block
                break

        if headline is None:

            print(
                "Could not find headline block:",
                headline_block_number
            )

            continue

        # =================================================
        # PRINT HEADLINE INFORMATION
        # =================================================

        print()
        print("#" * 110)
        print(
            f"ARTICLE CANDIDATE {article_number}"
        )
        print("#" * 110)

        print()
        print("HEADLINE:")
        print(headline["text"])

        print()
        print(
            f"Page: {headline['page']} | "
            f"Block: {headline['block']}"
        )

        print(
            f"x0={headline['x0']} | "
            f"x1={headline['x1']} | "
            f"y0={headline['y0']} | "
            f"y1={headline['y1']}"
        )

        print(
            f"Width={headline['width']} | "
            f"Height={headline['height']}"
        )

        print(
            f"Font={headline.get('max_font_size', 0)} | "
            f"Bold ratio={headline.get('bold_ratio', 0)}"
        )

        print(
            f"Relevance={headline.get('agriculture_relevance')} | "
            f"Score={headline.get('agriculture_score')}"
        )

        # =================================================
        # FIND NEARBY BLOCKS
        # =================================================

        nearby_blocks = []

        for block in blocks:

            if block["page"] != page:
                continue

            if block["block"] == headline["block"]:
                continue

            score = score_nearby_block(
                headline,
                block
            )

            if score <= 0:
                continue

            nearby_blocks.append(
                (
                    score,
                    block
                )
            )

        # -------------------------------------------------
        # Sort nearby blocks
        # -------------------------------------------------

        nearby_blocks.sort(
            key=lambda item: (
                -item[0],
                vertical_gap(
                    headline,
                    item[1]
                )
            )
        )

        # =================================================
        # PRINT NEARBY BLOCKS
        # =================================================

        print()
        print("-" * 110)
        print("NEARBY BLOCKS")
        print("-" * 110)

        for number, (score, block) in enumerate(
            nearby_blocks[:20],
            start=1
        ):

            gap = vertical_gap(
                headline,
                block
            )

            overlap = horizontal_overlap(
                headline,
                block
            )

            print()
            print(
                f"[{number}] "
                f"Candidate score={score}"
            )

            print(
                f"Block {block['block']} | "
                f"x={block['x0']} | "
                f"y={block['y0']} | "
                f"width={block['width']}"
            )

            print(
                f"Vertical gap={round(gap, 2)} | "
                f"Horizontal overlap={round(overlap, 2)}"
            )

            print(
                f"Font={block.get('max_font_size', 0)} | "
                f"Relevance={block.get('agriculture_relevance')} | "
                f"Score={block.get('agriculture_score')}"
            )

            print("TEXT:")
            print(block["text"])

            print("-" * 80)

    print()
    print("=" * 110)
    print("END OF DIAGNOSTIC")
    print("=" * 110)