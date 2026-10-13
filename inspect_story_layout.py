import json
from pathlib import Path


merged_folder = Path("data/merged_blocks")
articles_folder = Path("data/articles")


def find_block(blocks, page, block_number):

    for block in blocks:

        if (
            block["page"] == page
            and block["block"] == block_number
        ):
            return block

    return None


for article_file in articles_folder.glob("*_articles.json"):

    print()
    print("=" * 100)
    print("STORY LAYOUT")
    print("=" * 100)
    print("FILE:", article_file.name)

    merged_file = (
        merged_folder /
        article_file.name.replace(
            "_blocks_articles.json",
            "_blocks.json"
        )
    )

    if not merged_file.exists():
        print("Merged file not found.")
        continue

    with open(article_file, "r", encoding="utf-8") as file:
        articles = json.load(file)

    with open(merged_file, "r", encoding="utf-8") as file:
        blocks = json.load(file)

    for article_number, article in enumerate(
        articles,
        start=1
    ):

        headline = find_block(
            blocks,
            article["page"],
            article["headline_block"]
        )

        if headline is None:
            continue

        page = headline["page"]

        print()
        print("#" * 100)
        print(
            f"ARTICLE {article_number}: "
            f"{headline['text']}"
        )
        print("#" * 100)

        print()

        page_blocks = [
            block
            for block in blocks
            if block["page"] == page
        ]

        # -------------------------------------------------
        # Create rough horizontal zones
        # -------------------------------------------------

        min_x = min(
            block["x0"]
            for block in page_blocks
        )

        max_x = max(
            block["x1"]
            for block in page_blocks
        )

        page_width = max_x - min_x

        print(
            f"Page width approximately: "
            f"{round(page_width, 1)}"
        )

        print()

        # -------------------------------------------------
        # Print blocks in physical layout order
        # -------------------------------------------------

        page_blocks.sort(
            key=lambda block: (
                block["y0"],
                block["x0"]
            )
        )

        for block in page_blocks:

            # Only show blocks below headline
            if block["y0"] < headline["y0"]:
                continue

            # Ignore blocks extremely far below
            if block["y0"] > headline["y1"] + 500:
                continue

            # Distance from headline
            vertical_distance = (
                block["y0"] - headline["y1"]
            )

            if block["block"] == headline["block"]:
                marker = "HEADLINE"
            elif block.get(
                "agriculture_relevance"
            ) == "HIGH":
                marker = "HIGH"
            elif block.get(
                "agriculture_relevance"
            ) == "POSSIBLE":
                marker = "POSSIBLE"
            else:
                marker = "OTHER"

            print(
                f"{marker:8} | "
                f"B{block['block']:3} | "
                f"x={block['x0']:7.1f} | "
                f"y={block['y0']:7.1f} | "
                f"w={block['width']:7.1f} | "
                f"gap={vertical_distance:7.1f} | "
                f"font={block.get('max_font_size', 0):5.1f} | "
                f"{block['text'][:100]}"
            )

        print()

print()
print("=" * 100)
print("STORY LAYOUT INSPECTION COMPLETE")
print("=" * 100)