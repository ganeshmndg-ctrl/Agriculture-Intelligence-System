import json
from pathlib import Path


INPUT_DIR = Path("data/all_article_candidates")


def inspect_file(file):

    print()
    print("=" * 80)
    print(file.name)
    print("=" * 80)

    with open(
        file,
        "r",
        encoding="utf-8"
    ) as f:

        candidates = json.load(f)

    current_page = None

    for candidate in candidates:

        page = candidate.get(
            "page",
            ""
        )

        if page != current_page:

            current_page = page

            print()
            print(
                f"---------------- PAGE {page} ----------------"
            )

        block = candidate.get(
            "block_number",
            ""
        )

        text = candidate.get(
            "text",
            ""
        ).replace(
            "\n",
            " "
        ).strip()

        x0 = candidate.get(
            "x0",
            ""
        )

        y0 = candidate.get(
            "y0",
            ""
        )

        font = candidate.get(
            "max_font_size",
            ""
        )

        bold = candidate.get(
            "bold_ratio",
            ""
        )

        print(
            f"B{block:<5} "
            f"x={str(x0):<8} "
            f"y={str(y0):<8} "
            f"font={str(font):<6} "
            f"bold={str(bold):<6} "
            f"| {text}"
        )


def main():

    files = sorted(
        INPUT_DIR.glob(
            "*.json"
        )
    )

    if not files:

        print(
            "No candidate files found."
        )

        return

    for file in files:

        inspect_file(file)


if __name__ == "__main__":
    main()