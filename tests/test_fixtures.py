"""
test_fixtures.py — builds throwaway edge-case documents on demand for the test
suite (rather than shipping them as static binary files in the repo).
"""
import os
import io
from docx import Document
from docx.shared import Pt

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_fixtures")


def _ensure_dir():
    os.makedirs(FIXTURE_DIR, exist_ok=True)


def make_corrupt_docx():
    _ensure_dir()
    path = os.path.join(FIXTURE_DIR, "corrupt.docx")
    with open(path, "w") as f:
        f.write("this is not a real docx file, just plain text")
    return path


def make_empty_pdf():
    _ensure_dir()
    path = os.path.join(FIXTURE_DIR, "empty.pdf")
    open(path, "wb").close()
    return path


def make_docx_with_footer(filename, footer_text, body_text="Body content for edge-case test."):
    """Builds a docx with arbitrary raw footer text (single paragraph)."""
    _ensure_dir()
    doc = Document()
    footer = doc.sections[0].footer
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.text = footer_text
    doc.add_paragraph(body_text)
    path = os.path.join(FIXTURE_DIR, filename)
    doc.save(path)
    return path


def make_docx_with_table_footer(filename, cell_texts):
    """Builds a docx whose footer content lives in a table (common in real
    controlled templates), rather than a plain paragraph."""
    _ensure_dir()
    doc = Document()
    footer = doc.sections[0].footer
    table = footer.add_table(rows=1, cols=len(cell_texts), width=Pt(400))
    for i, text in enumerate(cell_texts):
        table.cell(0, i).text = text
    doc.add_paragraph("Body content for table-footer edge case.")
    path = os.path.join(FIXTURE_DIR, filename)
    doc.save(path)
    return path


def make_docx_no_footer(filename):
    """A docx with a completely empty/blank footer (template ID missing)."""
    _ensure_dir()
    doc = Document()
    doc.add_paragraph("Body content — no footer at all was stamped on this document.")
    path = os.path.join(FIXTURE_DIR, filename)
    doc.save(path)
    return path


def make_scanned_pdf_from(source_pdf_path, filename):
    """Rasterizes a text-based PDF into an image-only PDF to simulate a
    scanned document with no extractable text layer (real OCR fallback test)."""
    _ensure_dir()
    from pdf2image import convert_from_path
    import img2pdf

    pages = convert_from_path(source_pdf_path, dpi=150)
    img_bytes_list = []
    for p in pages:
        buf = io.BytesIO()
        p.save(buf, format="JPEG")
        img_bytes_list.append(buf.getvalue())
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, "wb") as f:
        f.write(img2pdf.convert(img_bytes_list))
    return path


def docx_to_pdf(docx_path):
    """Converts a docx to pdf via LibreOffice headless, returns the pdf path."""
    import subprocess
    subprocess.run(
        ["python3", "/mnt/skills/public/docx/scripts/office/soffice.py",
         "--headless", "--convert-to", "pdf",
         "--outdir", os.path.dirname(docx_path), docx_path],
        check=True, capture_output=True,
    )
    return os.path.splitext(docx_path)[0] + ".pdf"


def cleanup():
    import shutil
    if os.path.exists(FIXTURE_DIR):
        shutil.rmtree(FIXTURE_DIR)
