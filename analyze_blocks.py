import json
from pathlib import Path
from collections import Counter


# Location of our block data
blocks_folder = Path("data/blocks")


def repeated_character_ratio(text):
    """Return the proportion of the text made up by its most common character."""

    if not text:
        return 0

    counts = Counter(text)
    most_common_count = counts.most_common(1)[0][1]

    return most_common_count / len(text)


# Analyze each newspaper
for json_file in blocks_folder.glob("*.json"):

    print("=" * 70)
    print("FILE:", json_file.name)
    print("=" * 70)

    with open(json_file, "r", encoding="utf-8") as file:
        blocks = json.load(file)

    print("Total blocks:", len(blocks))
    print()

    # Find suspicious blocks
    suspicious_blocks = []

    for block in blocks:

        text = block["text"]

        ratio = repeated_character_ratio(text)

        # Very high repeated-character ratio
        if len(text) >= 30 and ratio >= 0.80:

            suspicious_blocks.append({
                "page": block["page"],
                "block": block["block"],
                "characters": len(text),
                "ratio": round(ratio, 2),
                "text": text[:100]
            })

    print("Potential artifact blocks:", len(suspicious_blocks))
    print()

    for block in suspicious_blocks[:20]:

        print(
            f"Page {block['page']} | "
            f"Block {block['block']} | "
            f"Chars {block['characters']} | "
            f"Ratio {block['ratio']}"
        )

        print(block["text"])
        print("-" * 50)