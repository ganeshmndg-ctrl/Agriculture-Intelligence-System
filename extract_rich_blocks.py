import pymupdf
import json
from pathlib import Path


# Folder containing newspaper PDFs
newspaper_folder = Path("Newspapers/Raw")

# Folder for richer block information
output_folder = Path("data/rich_blocks")
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

        page_data = page.get_text("dict")

        block_counter = 0

        for raw_block in page_data["blocks"]:

            # We only want text blocks
            if raw_block.get("type") != 0:
                continue

            block_counter += 1

            lines = raw_block.get("lines", [])

            all_text = []
            font_sizes = []
            fonts = []
            bold_spans = 0
            total_spans = 0

            for line in lines:

                line_text = []

                for span in line.get("spans", []):

                    text = span.get("text", "")

                    line_text.append(text)

                    font_sizes.append(span.get("size", 0))
                    fonts.append(span.get("font", ""))

                    total_spans += 1

                    # Check whether font appears bold
                    if "bold" in span.get("font", "").lower():
                        bold_spans += 1

                all_text.append("".join(line_text))

            # Clean line breaks and extra spaces
            clean_text = " ".join(
                " ".join(all_text).split()
            )

            if not clean_text:
                continue

            x0 = raw_block["bbox"][0]
            y0 = raw_block["bbox"][1]
            x1 = raw_block["bbox"][2]
            y1 = raw_block["bbox"][3]

            max_font_size = max(font_sizes) if font_sizes else 0
            min_font_size = min(font_sizes) if font_sizes else 0

            unique_fonts = list(set(fonts))

            bold_ratio = (
                bold_spans / total_spans
                if total_spans > 0
                else 0
            )

            block_data = {

                "page": page_number,

                "block": block_counter,

                "x0": round(x0, 2),
                "y0": round(y0, 2),
                "x1": round(x1, 2),
                "y1": round(y1, 2),

                "width": round(x1 - x0, 2),
                "height": round(y1 - y0, 2),

                "text": clean_text,

                "characters": len(clean_text),

                "line_count": len(lines),

                "min_font_size": round(min_font_size, 2),
                "max_font_size": round(max_font_size, 2),

                "fonts": unique_fonts,

                "bold_ratio": round(bold_ratio, 2)
            }

            newspaper_blocks.append(block_data)

    document.close()

    # Save output
    output_file = output_folder / f"{pdf_path.stem}_rich_blocks.json"

    with open(output_file, "w", encoding="utf-8") as file:

        json.dump(
            newspaper_blocks,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("Total text blocks:", len(newspaper_blocks))
    print("Saved to:", output_file)
    print("-" * 70)