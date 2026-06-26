import os
import re
from pypdf import PdfReader, PdfWriter

def extract_number(filename):
    match = re.search(r'\d+', filename)
    return int(match.group()) if match else 0

def merge_pdfs(folder_path, output_file):
    writer = PdfWriter()

    # check folder exists
    if not os.path.exists(folder_path):
        print("❌ Folder not found:", folder_path)
        return

    pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]

    if not pdf_files:
        print("❌ No PDF files found in folder")
        return

    # sort by number (file 1, file 2, file 10 correct order)
    pdf_files.sort(key=extract_number)

    print("\n📄 Files will be merged in this order:")
    for f in pdf_files:
        print(" -", f)

    # merge PDFs
    for pdf in pdf_files:
        path = os.path.join(folder_path, pdf)
        print(f"Adding: {pdf}")

        reader = PdfReader(path)

        for page in reader.pages:
            writer.add_page(page)

    # save output
    with open(output_file, "wb") as f:
        writer.write(f)

    print(f"\n✅ Merged successfully: {output_file}")



# ===== AUTO PATH FIX =====
folder_path = os.path.join(os.getcwd(), "pdfs")
output_file = "merged_output.pdf"

merge_pdfs(folder_path, output_file)