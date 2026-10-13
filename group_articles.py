import json
from pathlib import Path

classified_folder = Path("data/merged_blocks")
output_folder = Path("data/articles")
output_folder.mkdir(parents=True, exist_ok=True)


def load_blocks(json_file):
    with open(json_file, "r", encoding="utf-8") as file:
        return json.load(file)


def get_relevant_pages(blocks):
    pages = {}

    for block in blocks:
        page = block["page"]

        if page not in pages:
            pages[page] = []

        pages[page].append(block)

    relevant_pages = []

    for page, page_blocks in pages.items():

        has_relevant_block = any(
            block.get("agriculture_relevance") in ["HIGH", "POSSIBLE"]
            for block in page_blocks
        )

        if has_relevant_block:
            relevant_pages.append(page)

    return pages, relevant_pages


def find_headline_candidates(page_blocks):
    candidates = []

    for block in page_blocks:

        relevance = block.get(
            "agriculture_relevance",
            "LOW"
        )

        font_size = block.get(
            "max_font_size",
            0
        )

        text = block["text"].strip()

        if not text:
            continue

        # A relevant block with a relatively large font
        # is a possible headline.
        if relevance in ["HIGH", "POSSIBLE"] and font_size >= 15:

            candidates.append(block)

    return candidates


for json_file in classified_folder.glob("*_blocks.json"):

    print("=" * 100)
    print("PROCESSING:", json_file.name)
    print("=" * 100)

    blocks = load_blocks(json_file)

    pages, relevant_pages = get_relevant_pages(blocks)

    print("Relevant pages:", relevant_pages)
    print()

    articles = []

    for page_number in relevant_pages:

        page_blocks = pages[page_number]

        # Sort physically
        page_blocks = sorted(
            page_blocks,
            key=lambda block: (
                block["y0"],
                block["x0"]
            )
        )

        headline_candidates = find_headline_candidates(
            page_blocks
        )

        print(
            f"PAGE {page_number}: "
            f"{len(headline_candidates)} headline candidates"
        )

        for candidate in headline_candidates:

            article = {
                "newspaper": json_file.stem.replace(
                    "_blocks",
                    ""
                ),
                "page": page_number,
                "headline_candidate": candidate["text"],
                "headline_block": candidate["block"],
                "headline_x": candidate["x0"],
                "headline_y": candidate["y0"],
                "blocks": []
            }

            articles.append(article)

            print(
                "  →",
                candidate["text"]
            )

    output_file = (
        output_folder /
        f"{json_file.stem}_articles.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            articles,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("Article candidates:", len(articles))
    print("Saved to:", output_file)
    print()


print("=" * 100)
print("ARTICLE CANDIDATE EXTRACTION COMPLETE")
print("=" * 100)