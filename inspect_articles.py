import json
from pathlib import Path


# Folder containing cleaned block files
clean_folder = Path("data/clean_blocks")


# Pages we want to inspect
pages_to_inspect = [3, 5]


# Process each newspaper
for json_file in clean_folder.glob("*_blocks.json"):

    print("=" * 80)
    print("NEWSPAPER:", json_file.name)
    print("=" * 80)

    with open(json_file, "r", encoding="utf-8") as file:
        blocks = json.load(file)

    for page_number in pages_to_inspect:

        page_blocks = [
            block
            for block in blocks
            if block["page"] == page_number
        ]

        if not page_blocks:
            continue

        print()
        print("-" * 80)
        print("PAGE:", page_number)
        print("NUMBER OF BLOCKS:", len(page_blocks))
        print("-" * 80)

        # Sort approximately from top to bottom,
        # then left to right
        page_blocks.sort(
            key=lambda block: (
                block["y0"],
                block["x0"]
            )
        )

        for block in page_blocks:

            print(
                f"Block {block['block']:3} | "
                f"x={block['x0']:7.1f} | "
                f"y={block['y0']:7.1f} | "
                f"w={block['width']:6.1f} | "
                f"h={block['height']:6.1f}"
            )

            print(
                "    ",
                block["text"][:180]
            )

        print()