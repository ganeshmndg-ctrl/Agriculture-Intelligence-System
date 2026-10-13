import json
from pathlib import Path
from difflib import SequenceMatcher


classified_folder = Path("data/classified")
rich_folder = Path("data/rich_blocks")
output_folder = Path("data/merged_blocks")

output_folder.mkdir(parents=True, exist_ok=True)


def normalize_text(text):
    """Make text easier to compare between extraction methods."""
    return " ".join(text.lower().split())


def similarity(text1, text2):
    return SequenceMatcher(
        None,
        normalize_text(text1),
        normalize_text(text2)
    ).ratio()


for classified_file in classified_folder.glob("*_blocks.json"):

    print("=" * 100)
    print("PROCESSING:", classified_file.name)
    print("=" * 100)

    # Corresponding rich-block file
    rich_file = rich_folder / (
        classified_file.stem.replace(
            "_blocks",
            "_rich_blocks"
        ) + ".json"
    )

    if not rich_file.exists():
        print("Rich block file not found:", rich_file)
        continue

    with open(
        classified_file,
        "r",
        encoding="utf-8"
    ) as file:
        classified_blocks = json.load(file)

    with open(
        rich_file,
        "r",
        encoding="utf-8"
    ) as file:
        rich_blocks = json.load(file)

    # Organise rich blocks by page
    rich_by_page = {}

    for block in rich_blocks:

        page = block["page"]

        if page not in rich_by_page:
            rich_by_page[page] = []

        rich_by_page[page].append(block)

    merged_blocks = []

    exact_matches = 0
    approximate_matches = 0
    unmatched = 0

    for classified in classified_blocks:

        page = classified["page"]
        text = classified["text"]

        candidates = rich_by_page.get(page, [])

        best_match = None
        best_score = 0

        # ------------------------------------------------
        # First try exact text match
        # ------------------------------------------------

        normalized_classified = normalize_text(text)

        for rich in candidates:

            normalized_rich = normalize_text(
                rich["text"]
            )

            if normalized_classified == normalized_rich:
                best_match = rich
                best_score = 1.0
                break

        # ------------------------------------------------
        # If exact match failed, use text similarity
        # ------------------------------------------------

        if best_match is None:

            for rich in candidates:

                score = similarity(
                    text,
                    rich["text"]
                )

                # Also consider physical position
                x_distance = abs(
                    classified["x0"] - rich["x0"]
                )

                y_distance = abs(
                    classified["y0"] - rich["y0"]
                )

                # Prefer nearby blocks
                if x_distance < 20 and y_distance < 20:
                    score += 0.05

                if score > best_score:
                    best_score = score
                    best_match = rich

        # ------------------------------------------------
        # Merge the information
        # ------------------------------------------------

        merged = classified.copy()

        if best_match is not None and best_score >= 0.85:

            # Add rich layout information
            merged["line_count"] = best_match.get(
                "line_count",
                0
            )

            merged["min_font_size"] = best_match.get(
                "min_font_size",
                0
            )

            merged["max_font_size"] = best_match.get(
                "max_font_size",
                0
            )

            merged["fonts"] = best_match.get(
                "fonts",
                []
            )

            merged["bold_ratio"] = best_match.get(
                "bold_ratio",
                0
            )

            merged["rich_match_score"] = round(
                best_score,
                3
            )

            if best_score == 1.0:
                exact_matches += 1
            else:
                approximate_matches += 1

        else:

            merged["line_count"] = 0
            merged["min_font_size"] = 0
            merged["max_font_size"] = 0
            merged["fonts"] = []
            merged["bold_ratio"] = 0
            merged["rich_match_score"] = 0

            unmatched += 1

        merged_blocks.append(merged)

    # ----------------------------------------------------
    # Save merged dataset
    # ----------------------------------------------------

    output_file = output_folder / classified_file.name

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            merged_blocks,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("Classified blocks:", len(classified_blocks))
    print("Exact matches:", exact_matches)
    print("Approximate matches:", approximate_matches)
    print("Unmatched:", unmatched)
    print()
    print("Saved to:", output_file)
    print()


print("=" * 100)
print("MERGING COMPLETE")
print("=" * 100)