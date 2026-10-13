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
    print("COLUMN INSPECTION")
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

    with open(
        article_file,
        "r",
        encoding="utf-8"
    ) as file:
        articles = json.load(file)

    with open(
        merged_file,
        "r",
        encoding="utf-8"
    ) as file:
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
        # Only show blocks below the headline
        # -------------------------------------------------

        page_blocks = [
            block
            for block in page_blocks
            if block["y0"] >= headline["y1"]
        ]

        # -------------------------------------------------
        # Sort by X position
        # -------------------------------------------------

        page_blocks.sort(
            key=lambda block: (
                block["x0"],
                block["y0"]
            )
        )

        print(
            f"{'BLOCK':>6} | "
            f"{'X0':>8} | "
            f"{'X1':>8} | "
            f"{'WIDTH':>8} | "
            f"{'Y0':>8} | "
            f"TEXT"
        )

        print("-" * 120)

        for block in page_blocks:

            text = block["text"]

            if len(text) > 90:
                text = text[:90] + "..."

            print(
                f"{block['block']:>6} | "
                f"{block['x0']:>8.1f} | "
                f"{block['x1']:>8.1f} | "
                f"{block['width']:>8.1f} | "
                f"{block['y0']:>8.1f} | "
                f"{text}"
            )

        print()


print()
print("=" * 100)
print("COLUMN INSPECTION COMPLETE")
print("=" * 100)