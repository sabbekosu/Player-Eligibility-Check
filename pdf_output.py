import pdfplumber

# File path
im_pdf = 'imwintersoccer.pdf'

# Open the PDF and extract all text
with pdfplumber.open(im_pdf) as pdf:
    for page_num, page in enumerate(pdf.pages, start=1):
        text = page.extract_text()
        print(f"=== Page {page_num} ===\n")
        print(text)
        print("\n====================\n")