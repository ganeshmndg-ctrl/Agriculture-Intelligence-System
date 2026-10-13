import json
from pathlib import Path


grouped_folder = Path("data/grouped_articles")


for json_file in grouped_folder.glob("*_grouped.json"):

    print()
    print("=" * 100)
    print("FILE:", json_file.name)
    print("=" * 100)

    with open(
        json_file,
        "r",
        encoding="utf-8"
    ) as file:

        articles = json.load(file)

    for article_number, article in enumerate(
        articles,
        start=1
    ):

        print()
        print("#" * 100)
        print(
            f"ARTICLE {article_number}: "
            f"{article['headline']}"
        )
        print("#" * 100)

        print()

        print(
            "Newspaper:",
            article["newspaper"]
        )

        print(
            "Page:",
            article["page"]
        )

        print(
            "Story blocks:",
            article["story_block_count"]
        )

        print(
            "Block numbers:",
            [
                block["block"]
                for block in article["blocks"]
            ]
        )

        print()
        print("-" * 100)
        print("ARTICLE TEXT")
        print("-" * 100)
        print()

        print(
            article["article_text"]
        )

        print()
        print("=" * 100)