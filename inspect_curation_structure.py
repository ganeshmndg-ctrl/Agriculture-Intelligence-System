import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "curated_intelligence_v23"
    / "CURATED_INTELLIGENCE_v23.json"
)


def describe(value, indent=0, max_depth=4):

    prefix = " " * indent

    if isinstance(value, dict):

        print(
            f"{prefix}DICT "
            f"({len(value)} keys)"
        )

        for i, (key, child) in enumerate(value.items()):

            if i >= 30:
                print(
                    f"{prefix}  ... more keys ..."
                )
                break

            print(
                f"{prefix}  KEY: {key}"
            )

            if indent // 2 < max_depth:

                if isinstance(child, (dict, list)):

                    describe(
                        child,
                        indent + 4,
                        max_depth
                    )

                else:

                    value_preview = str(child)

                    if len(value_preview) > 150:
                        value_preview = (
                            value_preview[:150]
                            + "..."
                        )

                    print(
                        f"{prefix}      VALUE: "
                        f"{value_preview}"
                    )

    elif isinstance(value, list):

        print(
            f"{prefix}LIST "
            f"({len(value)} items)"
        )

        if value:

            print(
                f"{prefix}  FIRST ITEM:"
            )

            describe(
                value[0],
                indent + 4,
                max_depth
            )

    else:

        print(
            f"{prefix}{type(value).__name__}: "
            f"{str(value)[:150]}"
        )


def main():

    print("=" * 80)
    print(
        "CURATED INTELLIGENCE V2.3 "
        "STRUCTURE INSPECTOR"
    )
    print("=" * 80)

    if not INPUT_FILE.exists():

        print()
        print(
            "ERROR: V2.3 curated file not found:"
        )
        print(INPUT_FILE)
        return

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    print()
    print("FILE:")
    print(INPUT_FILE)

    print()
    print("TOP-LEVEL STRUCTURE:")
    describe(data)

    print()
    print("=" * 80)
    print("END")
    print("=" * 80)


if __name__ == "__main__":
    main()