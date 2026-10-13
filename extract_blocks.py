import pymupdf
import json
from pathlib import Path


# Folder containing newspaper PDFs
newspaper_folder = Path("Newspapers/Raw")

# Folder where block data will be saved
output_folder = Path("data/blocks")
output_folder.mkdir(parents=True, exist_ok=True)


# Find all newspapers
pdf_files = list(newspaper_folder.glob("*.pdf"))

print("Newspapers found:", len(pdf_files))
print()


for pdf_path in pdf_files:

    print("Processing:", pdf_path.name)

    document = pymupdf.open(pdf_path)

    newspaper_blocks = []

    # Process every page
    for page_number, page in enumerate(document, start=1):

        blocks = page.get_text("blocks")

        for block_number, block in enumerate(blocks, start=1):

            x0, y0, x1, y1, text, _, block_type = block

            clean_text = " ".join(text.split())

            block_data = {
                "page": page_number,
                "block": block_number,
                "x0": round(x0, 2),
                "y0": round(y0, 2),
                "x1": round(x1, 2),
                "y1": round(y1, 2),
                "width": round(x1 - x0, 2),
                "height": round(y1 - y0, 2),
                "text": clean_text,
                "characters": len(clean_text),
                "block_type": block_type
            }

            newspaper_blocks.append(block_data)

    document.close()

    # Output filename
    output_file = output_folder / f"{pdf_path.stem}_blocks.json"

    # Save structured data
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(newspaper_blocks, file, ensure_ascii=False, indent=2)

    print("Total blocks:", len(newspaper_blocks))
    print("Saved to:", output_file)
    print("-" * 60)