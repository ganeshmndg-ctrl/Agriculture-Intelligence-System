import json
from pathlib import Path

classified_folder = Path("data/classified")

# Choose the newspaper and page you want to inspect
file_name = "BS Mumbai 16-09-2026_blocks.json"
page_to_inspect = 9

file_path = classified_folder / file_name

with open(file_path, "r", encoding="utf-8") as file:
    blocks = json.load(file)

# Get blocks from the selected page
page_blocks = [
    block
    for block in blocks
    if block["page"] == page_to_inspect
]

# Sort from top to bottom, then left to right
page_blocks = sorted(
    page_blocks,
    key=lambda block: (
        block["y0"],
        block["x0"]
    )
)

print("=" * 100)
print("NEWSPAPER:", file_name)
print("PAGE:", page_to_inspect)
print("TOTAL BLOCKS:", len(page_blocks))
print("=" * 100)

for block in page_blocks:

    print()
    print(
        f"Block {block['block']} | "
        f"x={block['x0']} | "
        f"y={block['y0']} | "
        f"width={block['width']} | "
        f"height={block['height']}"
    )

    print(
        f"Relevance: "
        f"{block.get('agriculture_relevance', 'UNKNOWN')} | "
        f"Score: "
        f"{block.get('agriculture_score', 0)}"
    )

    print("Text:")
    print(block["text"])

    print("-" * 100)