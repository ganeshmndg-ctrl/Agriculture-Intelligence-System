import pymupdf
from pathlib import Path

# Folder containing newspaper PDFs
newspaper_folder = Path("Newspapers/Raw")

# Folder where extracted text will be saved
output_folder = Path("data/extracted_text")
output_folder.mkdir(parents=True, exist_ok=True)

# Find all PDF files
pdf_files = list(newspaper_folder.glob("*.pdf"))

print("Newspapers found:", len(pdf_files))
print()

# Process every newspaper
for pdf_path in pdf_files:

    print("Processing:", pdf_path.name)

    document = pymupdf.open(pdf_path)

    all_text = []

    # Read every page
    for page_number, page in enumerate(document, start=1):

        text = page.get_text()

        # Add page number before the extracted text
        all_text.append(
            f"\n\n===== PAGE {page_number} =====\n\n{text}"
        )

    # Combine all pages
    full_text = "".join(all_text)

    # Create output filename
    output_file = output_folder / f"{pdf_path.stem}.txt"

    # Save extracted text
    output_file.write_text(full_text, encoding="utf-8")

    print("Pages extracted:", len(document))
    print("Characters extracted:", len(full_text))
    print("Saved to:", output_file)
    print("-" * 50)

    document.close()