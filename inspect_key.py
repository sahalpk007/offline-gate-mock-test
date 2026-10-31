import pymupdf

# Point the diagnostic at a local answer-key PDF.
key_path = r"keys\CS1_2026_Keys.pdf"

with pymupdf.open(key_path) as document:
    for page_number, page in enumerate(document, start=1):
        # Report the text and tables detected on this page.
        text = page.get_text("text")
        tables = page.find_tables().tables
        print(f"\nPAGE {page_number}: text_chars={len(text)}, tables={len(tables)}")

        for table_number, table in enumerate(tables, start=1):
            # Preview the first eight extracted rows from each table.
            rows = table.extract()
            print(f"TABLE {table_number}: rows={len(rows)}")

            for row in rows[:8]:
                print(repr(row))