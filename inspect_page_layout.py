import json
from pathlib import Path
from collections import defaultdict


# ============================================================
# AGRICULTURE INTELLIGENCE SYSTEM
# PAGE LAYOUT DIAGNOSTIC
#
# Purpose:
#   Inspect the physical structure of newspaper pages.
#
#   We are NOT grouping articles yet.
#
#   This script helps us understand:
#       - columns
#       - blocks
#       - headlines
#       - body text
#       - charts / tables
#       - advertisements
#       - page furniture
#
# Output:
#   data/page_layout_diagnostics/
#
# ============================================================


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RICH_DIR = BASE_DIR / "data" / "rich_blocks"

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "page_layout_diagnostics"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# SETTINGS
# ============================================================

# Pages we want to inspect.
#
# These are deliberately selected because they contain
# several different types of stories.
#
# BS:
#   Page 1 = major headlines
#   Page 3 = multiple business/economy stories
#   Page 4 = stocks/company stories
#
# ET:
#   Page 3 = many major stories
#   Page 9 = drought/agriculture/markets
#   Page 20 = trade/rice/ethanol
#
INSPECT_PAGES = {
    "BS Mumbai 16-09-2026": [1, 3, 4],
    "ET Mumbai 16-09-2026": [3, 9, 20],
}


# ============================================================
# LOAD JSON
# ============================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    return " ".join(
        str(text).split()
    )


# ============================================================
# WIDTH
# ============================================================

def get_width(block):

    return max(
        0,
        block["x1"] - block["x0"]
    )


# ============================================================
# HEIGHT
# ============================================================

def get_height(block):

    return max(
        0,
        block["y1"] - block["y0"]
    )


# ============================================================
# NOISE CHECK
# ============================================================

NOISE_TERMS = [
    "www.business-standard.com",
    "www.business-standard",
    "published simultaneously",
    "economic times",
    "the economic times",
    "group +91",
    "whatsapp",
]


def is_noise(text):

    text_lower = clean_text(
        text
    ).lower()

    for term in NOISE_TERMS:

        if term in text_lower:
            return True

    return False


# ============================================================
# PROBABLE HEADLINE
# ============================================================

def probable_headline(block):

    text = clean_text(
        block["text"]
    )

    if not text:
        return False

    if is_noise(text):
        return False

    if len(text) < 12:
        return False

    if len(text) > 160:
        return False

    if block.get(
        "line_count",
        0
    ) > 5:
        return False

    font = block.get(
        "min_font_size",
        0
    )

    max_font = block.get(
        "max_font_size",
        0
    )

    bold = block.get(
        "bold_ratio",
        0
    )

    if max_font >= 15:
        return True

    if font >= 12:
        return True

    if (
        font >= 10
        and
        bold > 0.15
    ):
        return True

    return False


# ============================================================
# COLUMN ESTIMATION
# ============================================================

def estimate_columns(blocks):

    """
    Estimate rough physical columns using x0 positions.

    IMPORTANT:
    This is diagnostic only.

    We are NOT claiming these are the final article
    boundaries.
    """

    if not blocks:

        return []

    # --------------------------------------------------------
    # Collect left edges
    # --------------------------------------------------------

    x_positions = sorted(
        set(
            round(
                block["x0"],
                1
            )
            for block in blocks
        )
    )

    # --------------------------------------------------------
    # Cluster nearby x positions
    # --------------------------------------------------------

    clusters = []

    current = []

    previous = None

    for x in x_positions:

        if previous is None:

            current = [x]

        elif (
            x - previous
            <= 35
        ):

            current.append(x)

        else:

            clusters.append(
                current
            )

            current = [x]

        previous = x

    if current:

        clusters.append(
            current
        )

    # --------------------------------------------------------
    # Convert cluster to representative x
    # --------------------------------------------------------

    representatives = []

    for cluster in clusters:

        representatives.append(
            sum(cluster)
            /
            len(cluster)
        )

    return representatives


# ============================================================
# ASSIGN COLUMN
# ============================================================

def assign_column(
    block,
    column_positions
):

    if not column_positions:

        return None

    x = block["x0"]

    distances = [
        abs(
            x - column_x
        )
        for column_x
        in column_positions
    ]

    nearest = min(
        range(
            len(distances)
        ),
        key=lambda i:
            distances[i]
    )

    return nearest + 1


# ============================================================
# PRINT BLOCK
# ============================================================

def format_block(
    block,
    column_number
):

    text = clean_text(
        block["text"]
    )

    # Keep console readable
    if len(text) > 180:

        text = (
            text[:177]
            + "..."
        )

    headline_flag = (
        "HEADLINE?"
        if probable_headline(
            block
        )
        else ""
    )

    noise_flag = (
        "NOISE?"
        if is_noise(
            block["text"]
        )
        else ""
    )

    return (
        f""
        f"[B{block['block']:>3}] "
        f"COL {str(column_number):>2} "
        f"X={block['x0']:>7.1f} "
        f"Y={block['y0']:>7.1f} "
        f"W={get_width(block):>7.1f} "
        f"H={get_height(block):>6.1f} "
        f"FONT={block.get('min_font_size', 0):>5.1f} "
        f"LINES={block.get('line_count', 0):>2} "
        f"{headline_flag:<10} "
        f"{noise_flag:<6} "
        f"| {text}"
    )


# ============================================================
# ANALYZE ONE PAGE
# ============================================================

def analyze_page(
    newspaper_name,
    page_number,
    all_blocks
):

    page_blocks = [
        block
        for block in all_blocks
        if block["page"] == page_number
    ]

    if not page_blocks:

        return (
            f"\nPAGE {page_number}: "
            "NO BLOCKS FOUND\n"
        )

    # --------------------------------------------------------
    # Sort physically
    # --------------------------------------------------------

    page_blocks.sort(
        key=lambda b: (
            b["y0"],
            b["x0"]
        )
    )

    # --------------------------------------------------------
    # Estimate columns
    # --------------------------------------------------------

    column_positions = (
        estimate_columns(
            page_blocks
        )
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    output = []

    output.append(
        "\n"
        + "=" * 100
    )

    output.append(
        f"{newspaper_name} | PAGE {page_number}"
    )

    output.append(
        "=" * 100
    )

    output.append(
        f"Total blocks: "
        f"{len(page_blocks)}"
    )

    output.append(
        "Estimated column left-edges: "
        +
        str(
            [
                round(
                    x,
                    1
                )
                for x in column_positions
            ]
        )
    )

    output.append(
        ""
    )

    # --------------------------------------------------------
    # HEADLINE SUMMARY
    # --------------------------------------------------------

    output.append(
        "-" * 100
    )

    output.append(
        "PROBABLE HEADLINE BLOCKS"
    )

    output.append(
        "-" * 100
    )

    headline_blocks = []

    for block in page_blocks:

        if probable_headline(
            block
        ):

            headline_blocks.append(
                block
            )

    if not headline_blocks:

        output.append(
            "No probable headlines."
        )

    else:

        for block in headline_blocks:

            column = assign_column(
                block,
                column_positions
            )

            text = clean_text(
                block["text"]
            )

            output.append(
                f"B{block['block']} | "
                f"COL {column} | "
                f"X={block['x0']:.1f} "
                f"Y={block['y0']:.1f} | "
                f"FONT={block.get('min_font_size', 0):.1f} | "
                f"{text}"
            )

    # --------------------------------------------------------
    # ALL BLOCKS
    # --------------------------------------------------------

    output.append(
        ""
    )

    output.append(
        "-" * 100
    )

    output.append(
        "ALL BLOCKS IN PHYSICAL ORDER"
    )

    output.append(
        "-" * 100
    )

    # --------------------------------------------------------
    # Group blocks by approximate column
    # --------------------------------------------------------

    column_groups = defaultdict(list)

    for block in page_blocks:

        column = assign_column(
            block,
            column_positions
        )

        column_groups[
            column
        ].append(
            block
        )

    # --------------------------------------------------------
    # Print column by column
    # --------------------------------------------------------

    for column_number in sorted(
        column_groups.keys()
    ):

        output.append(
            ""
        )

        output.append(
            f"################ COLUMN "
            f"{column_number} ################"
        )

        output.append(
            ""
        )

        blocks = column_groups[
            column_number
        ]

        blocks.sort(
            key=lambda b: (
                b["y0"],
                b["x0"]
            )
        )

        for block in blocks:

            output.append(
                format_block(
                    block,
                    column_number
                )
            )

    return "\n".join(
        output
    )


# ============================================================
# PROCESS NEWSPAPER
# ============================================================

def process_newspaper(
    rich_file
):

    newspaper_name = (
        rich_file
        .stem
        .replace(
            "_rich_blocks",
            ""
        )
    )

    print()
    print(
        "=" * 100
    )

    print(
        newspaper_name
    )

    print(
        "=" * 100
    )

    blocks = load_json(
        rich_file
    )

    pages_to_inspect = (
        INSPECT_PAGES.get(
            newspaper_name,
            []
        )
    )

    if not pages_to_inspect:

        print(
            "No pages configured."
        )

        return

    all_output = []

    for page_number in pages_to_inspect:

        result = analyze_page(
            newspaper_name,
            page_number,
            blocks
        )

        all_output.append(
            result
        )

        print(
            result
        )

    # --------------------------------------------------------
    # Save diagnostic file
    # --------------------------------------------------------

    output_file = (
        OUTPUT_DIR
        /
        f"{newspaper_name}"
        "_layout_diagnostic.txt"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n\n".join(
                all_output
            )
        )

    print()
    print(
        "Saved diagnostic:"
    )

    print(
        output_file
    )


# ============================================================
# MAIN
# ============================================================

def main():

    rich_files = sorted(
        RICH_DIR.glob(
            "*_rich_blocks.json"
        )
    )

    if not rich_files:

        print(
            "No rich block files found."
        )

        print(
            RICH_DIR
        )

        return

    print(
        f"Found "
        f"{len(rich_files)} "
        f"rich-block file(s)."
    )

    for rich_file in rich_files:

        process_newspaper(
            rich_file
        )

    print()
    print(
        "=" * 100
    )

    print(
        "PAGE LAYOUT DIAGNOSTIC COMPLETE"
    )

    print(
        "=" * 100
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()