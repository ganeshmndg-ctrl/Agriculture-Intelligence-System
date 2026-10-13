from pathlib import Path
import json


# ============================================================
# GOVERNMENT INTELLIGENCE BANK
# ONE-TIME ENCODING REPAIR
# ============================================================

BANK_PATH = Path(
    "data/government_intelligence_bank_v2/"
    "GOVERNMENT_INTELLIGENCE_BANK_v2.json"
)


REPLACEMENTS = {
    # Rupee symbol
    "â‚¹": "₹",

    # Common UTF-8 mojibake
    "â€“": "–",
    "â€”": "—",
    "â€œ": "“",
    "â€": "”",
    "â€˜": "‘",
    "â€™": "’",
    "â€¦": "…",
    "Â°": "°",
    "Â": "",
}


def repair_text(value):
    """
    Recursively repair mojibake in strings.
    """
    if isinstance(value, str):
        repaired = value

        # Apply replacements repeatedly in case a string
        # contains more than one corrupted sequence.
        for _ in range(3):
            old = repaired

            for bad, good in REPLACEMENTS.items():
                repaired = repaired.replace(bad, good)

            if repaired == old:
                break

        return repaired

    elif isinstance(value, list):
        return [repair_text(item) for item in value]

    elif isinstance(value, dict):
        return {
            key: repair_text(value)
            for key, value in value.items()
        }

    return value


def count_bad_strings(value):
    """
    Count remaining known mojibake strings recursively.
    """
    count = 0

    if isinstance(value, str):
        for bad in REPLACEMENTS:
            if bad in value:
                count += 1
                break

    elif isinstance(value, list):
        for item in value:
            count += count_bad_strings(item)

    elif isinstance(value, dict):
        for item in value.values():
            count += count_bad_strings(item)

    return count


def main():

    print("=" * 80)
    print("GOVERNMENT INTELLIGENCE BANK")
    print("ENCODING REPAIR")
    print("=" * 80)

    if not BANK_PATH.exists():
        print()
        print("ERROR: Government Intelligence Bank JSON was not found.")
        print(BANK_PATH.resolve())
        return

    print()
    print("Loading Government Intelligence Bank...")

    with open(BANK_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    before_bad = count_bad_strings(data)

    print(f"Known corrupted strings before repair: {before_bad}")

    print()
    print("Repairing text recursively...")

    repaired_data = repair_text(data)

    after_bad = count_bad_strings(repaired_data)

    # Write back with proper UTF-8.
    with open(
        BANK_PATH,
        "w",
        encoding="utf-8",
        newline="\n"
    ) as f:
        json.dump(
            repaired_data,
            f,
            ensure_ascii=False,
            indent=2
        )

        # Final newline
        f.write("\n")

    print()
    print("Encoding repair complete.")
    print()
    print(f"Known corrupted strings after repair: {after_bad}")

    print()
    print("Updated file:")
    print(BANK_PATH.resolve())

    print()
    print("No structural fields were changed.")
    print("No records were added or removed.")

    if after_bad == 0:
        print()
        print("STATUS: SUCCESS")
        print("All known mojibake patterns were removed.")
    else:
        print()
        print("STATUS: WARNING")
        print(
            "Some known mojibake patterns remain. "
            "The JSON should be inspected before proceeding."
        )


if __name__ == "__main__":
    main()