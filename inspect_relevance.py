import json
from pathlib import Path

classified_folder = Path("data/classified")


for json_file in classified_folder.glob("*_blocks.json"):

    print("=" * 90)
    print("NEWSPAPER:", json_file.name)
    print("=" * 90)

    with open(json_file, "r", encoding="utf-8") as file:
        blocks = json.load(file)

    high_blocks = [
        block
        for block in blocks
        if block.get("agriculture_relevance") == "HIGH"
    ]

    possible_blocks = [
        block
        for block in blocks
        if block.get("agriculture_relevance") == "POSSIBLE"
    ]

    print()
    print("HIGH RELEVANCE:", len(high_blocks))
    print("POSSIBLE RELEVANCE:", len(possible_blocks))
    print()


    # ========================================================
    # HIGH RELEVANCE
    # ========================================================

    print("#" * 90)
    print("HIGH RELEVANCE BLOCKS")
    print("#" * 90)

    for number, block in enumerate(high_blocks, start=1):

        print()
        print(f"[HIGH {number}]")

        print(
            f"Page: {block['page']} | "
            f"Block: {block['block']} | "
            f"Score: {block.get('agriculture_score', 0)}"
        )

        print(
            "Strong keywords:",
            ", ".join(block.get("strong_keywords", []))
        )

        print(
            "Context keywords:",
            ", ".join(block.get("context_keywords", []))
        )

        print(
            "Negative keywords:",
            ", ".join(block.get("negative_keywords", []))
        )

        print("Text:")
        print(block["text"])

        print("-" * 90)


    # ========================================================
    # POSSIBLE RELEVANCE
    # ========================================================

    print()
    print("#" * 90)
    print("POSSIBLE RELEVANCE BLOCKS")
    print("#" * 90)

    for number, block in enumerate(possible_blocks, start=1):

        print()
        print(f"[POSSIBLE {number}]")

        print(
            f"Page: {block['page']} | "
            f"Block: {block['block']} | "
            f"Score: {block.get('agriculture_score', 0)}"
        )

        print(
            "Strong keywords:",
            ", ".join(block.get("strong_keywords", []))
        )

        print(
            "Context keywords:",
            ", ".join(block.get("context_keywords", []))
        )

        print(
            "Negative keywords:",
            ", ".join(block.get("negative_keywords", []))
        )

        print("Text:")
        print(block["text"])

        print("-" * 90)


    print()
    print("=" * 90)
    print("END OF", json_file.name)
    print("=" * 90)
    print()