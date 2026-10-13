import pymupdf

pdf_path = "Newspapers/Raw/BS Mumbai 16-09-2026.pdf"

document = pymupdf.open(pdf_path)

# Inspect PDF page 5
page_number = 5
page = document[page_number - 1]

blocks = page.get_text("blocks")

print(f"PDF page: {page_number}")
print(f"Number of text blocks: {len(blocks)}")
print()

for i, block in enumerate(blocks, start=1):

    x0, y0, x1, y1, text, block_number, block_type = block

    clean_text = " ".join(text.split())

    width = x1 - x0
    height = y1 - y0

    print(
        f"{i:03} | "
        f"x={x0:7.1f} | "
        f"y={y0:7.1f} | "
        f"w={width:6.1f} | "
        f"h={height:6.1f} | "
        f"chars={len(clean_text):4} | "
        f"{clean_text[:80]}"
    )

document.close()