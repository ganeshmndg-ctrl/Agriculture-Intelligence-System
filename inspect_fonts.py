import json
from pathlib import Path


rich_folder = Path("data/rich_blocks")


for json_file in rich_folder.glob("*_rich_blocks.json"):

    print("=" * 80)
    print("NEWSPAPER:", json_file.name)
    print("=" * 80)

    with open(json_file, "r", encoding="utf-8") as file:
        blocks = json.load(file)

    # Look only at page 3
    page_blocks = [
        block
        for block in blocks
        if block["page"] == 3
    ]

    # Sort from top to bottom, then left to right
    page_blocks.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    print("PAGE 3")
    print()

    for block in page_blocks:

        print(
            f"Block {block['block']:3} | "
            f"font={block['max_font_size']:5.1f} | "
            f"bold={block['bold_ratio']:4.2f} | "
            f"lines={block['line_count']:2} | "
            f"x={block['x0']:6.1f} | "
            f"y={block['y0']:6.1f}"
        )

        print(
            "    ",
            block["text"][:120]
        )

    print()