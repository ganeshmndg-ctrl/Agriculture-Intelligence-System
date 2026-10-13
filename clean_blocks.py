import json
from pathlib import Path
from collections import Counter


# Input folder
blocks_folder = Path("data/blocks")

# Output folder
clean_folder = Path("data/clean_blocks")
clean_folder.mkdir(parents=True, exist_ok=True)


def repeated_character_ratio(text):
    """Calculate how much of the text consists of one repeated character."""

    if not text:
        return 0

    counts = Counter(text)
    most_common_count = counts.most_common(1)[0][1]

    return most_common_count / len(text)


def is_artifact(text):
    """Identify obvious PDF extraction artifacts."""

    if not text:
        return True

    # Check repeated-character artifacts
    if len(text) >= 30:

        ratio = repeated_character_ratio(text)

        if ratio >= 0.80:
            return True

    return False


# Process every newspaper
for json_file in blocks_folder.glob("*_blocks.json"):

    print("=" * 70)
    print("Processing:", json_file.name)
    print("=" * 70)

    with open(json_file, "r", encoding="utf-8") as file:
        blocks = json.load(file)

    cleaned_blocks = []
    removed_blocks = []

    for block in blocks:

        text = block["text"]

        if is_artifact(text):

            removed_blocks.append(block)

        else:

            cleaned_blocks.append(block)

    # Output filename
    output_file = clean_folder / json_file.name

    # Save cleaned blocks
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(
            cleaned_blocks,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("Original blocks:", len(blocks))
    print("Removed artifacts:", len(removed_blocks))
    print("Remaining blocks:", len(cleaned_blocks))
    print("Saved to:", output_file)
    print()