import json
from pathlib import Path


blocks_folder = Path("data/blocks")


# Find all newspaper block files
json_files = list(blocks_folder.glob("*_blocks.json"))


for json_file in json_files:

    print("=" * 70)
    print("NEWSPAPER:", json_file.name)
    print("=" * 70)

    with open(json_file, "r", encoding="utf-8") as file:
        blocks = json.load(file)

    print("Total blocks:", len(blocks))
    print()

    # Show first 20 blocks
    for block in blocks[:20]:

        print(
            f"Page {block['page']} | "
            f"Block {block['block']} | "
            f"{block['text'][:150]}"
        )

    print()