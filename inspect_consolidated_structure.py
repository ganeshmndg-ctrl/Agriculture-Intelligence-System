import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = (
    BASE_DIR
    / "data"
    / "consolidated_articles_v1"
)


def inspect_value(value, indent=0, max_depth=4):

    prefix = " " * indent

    if indent > max_depth * 4:
        print(
            prefix
            + f"<{type(value).__name__}>"
        )
        return

    if isinstance(value, dict):

        print(
            prefix
            + "{"
        )

        for key, child in value.items():

            print(
                prefix
                + f"  KEY: {key!r} "
                + f"TYPE: {type(child).__name__}"
            )

            if isinstance(child, (dict, list)):

                inspect_value(
                    child,
                    indent + 4,
                    max_depth
                )

            elif isinstance(child, str):

                preview = (
                    child
                    .replace("\n", " ")
                    .replace("\r", " ")
                )

                if len(preview) > 180:
                    preview = (
                        preview[:180]
                        + "..."
                    )

                print(
                    prefix
                    + f"      VALUE: {preview!r}"
                )

            else:

                print(
                    prefix
                    + f"      VALUE: {child!r}"
                )

        print(
            prefix
            + "}"
        )

    elif isinstance(value, list):

        print(
            prefix
            + f"[LIST length={len(value)}]"
        )

        for i, item in enumerate(value[:3]):

            print(
                prefix
                + f"  ITEM {i}: "
                + f"{type(item).__name__}"
            )

            inspect_value(
                item,
                indent + 4,
                max_depth
            )

        if len(value) > 3:

            print(
                prefix
                + f"  ... {len(value) - 3} more items"
            )

    else:

        print(
            prefix
            + repr(value)
        )


def main():

    files = sorted(
        INPUT_DIR.glob("*.json")
    )

    print("=" * 80)
    print("CONSOLIDATED JSON STRUCTURE INSPECTOR")
    print("=" * 80)

    print(
        f"Found {len(files)} files."
    )

    for file in files:

        print()
        print("=" * 80)
        print(
            f"FILE: {file.name}"
        )
        print("=" * 80)

        with open(
            file,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        print(
            f"Top-level type: "
            f"{type(data).__name__}"
        )

        if isinstance(data, dict):

            print()
            print("TOP-LEVEL KEYS:")

            for key in data.keys():

                value = data[key]

                if isinstance(value, list):

                    print(
                        f"  {key}: "
                        f"LIST "
                        f"(length={len(value)})"
                    )

                elif isinstance(value, dict):

                    print(
                        f"  {key}: DICT"
                    )

                else:

                    print(
                        f"  {key}: "
                        f"{type(value).__name__} "
                        f"= {value!r}"
                    )

        # ----------------------------------------------------
        # Inspect pages
        # ----------------------------------------------------

        pages = data.get("pages", [])

        print()
        print(
            f"PAGES: {len(pages)}"
        )

        for page_index, page in enumerate(
            pages[:2]
        ):

            print()
            print("-" * 80)
            print(
                f"PAGE RECORD {page_index}"
            )
            print("-" * 80)

            inspect_value(
                page,
                indent=0,
                max_depth=5
            )

        print()
        print(
            "End of file inspection."
        )


if __name__ == "__main__":
    main()