"""
Comprehensive test suite for the Outdated Template Detector.

Run with:  python3 tests/test_cases.py     (from anywhere)

Sections:
  A. Master list integrity      — the mock data itself is internally consistent
  B. Direct lookup verdicts     — checker.check() against every status/version combo
  C. End-to-end file tests      — the 4 shipped sample docx files
  D. Edge cases                 — everything found while stress-testing:
                                   case sensitivity, non-numeric versions, corrupt
                                   files, missing footers, table-layout footers,
                                   'Revision:' wording, scanned PDFs (real OCR)
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from checker import load_master_list, check, check_document
from extractor import extract
import test_fixtures as fx

MASTER_LIST = os.path.join(ROOT, "master_list.xlsx")
SAMPLE_DIR = os.path.join(ROOT, "sample_docs")

passed = 0
failed = 0
failures = []


def expect(description, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"[OK  ] {description}")
    else:
        failed += 1
        failures.append(description)
        print(f"[FAIL] {description}   {detail}")


# ============================================================================
print("=" * 78)
print("SECTION A — Master list integrity")
print("=" * 78)

master_df_raw = load_master_list(MASTER_LIST)
ids = list(master_df_raw.index)
expect("No duplicate Template_IDs in master list", len(ids) == len(set(ids)))

effective_ids = set(master_df_raw[master_df_raw["Status"] == "Effective"].index)
bad_refs = []
for tid, row in master_df_raw.iterrows():
    if row["Status"] == "Superseded":
        if not row["Superseded_By"] or row["Superseded_By"] not in effective_ids:
            bad_refs.append(tid)
expect("Every Superseded row's Superseded_By points to a valid Effective template",
       len(bad_refs) == 0, detail=str(bad_refs))

bad_status_values = set(master_df_raw["Status"]) - {"Effective", "Superseded", "Withdrawn"}
expect("All Status values are one of Effective/Superseded/Withdrawn",
       len(bad_status_values) == 0, detail=str(bad_status_values))


# ============================================================================
print()
print("=" * 78)
print("SECTION B — Direct lookup verdicts (checker.check)")
print("=" * 78)

master_df = load_master_list(MASTER_LIST)

DIRECT_CASES = [
    ("Effective template, exact latest version",       "V-QMS-0114221", "3.0", "PASS"),
    ("Effective template, older version (WARN)",        "V-QMS-0114221", "2.0", "WARN"),
    ("Effective template, much older version (WARN)",   "V-QMS-0114221", "1.0", "WARN"),
    ("Superseded template (FAIL)",                      "V-QMS-0114100", "2.0", "FAIL"),
    ("Withdrawn template, no replacement (FAIL)",       "V-QMS-0114050", "1.0", "FAIL"),
    ("Unknown/unregistered Template ID (FLAG)",         "V-QMS-9999999", "1.0", "FLAG"),
    ("Missing Template ID entirely (FLAG)",             None,            "1.0", "FLAG"),
    ("Effective template, version missing (FLAG)",      "V-QMS-0114230", None,  "FLAG"),
    ("Effective template, different ID at its latest",  "V-QMS-0114290", "1.0", "PASS"),
    ("Superseded ID pointing to valid replacement",     "V-QMS-0114205", "1.0", "FAIL"),
]
for desc, tid, ver, expected in DIRECT_CASES:
    result = check(tid, ver, master_df)
    expect(f"{desc:<48} expected={expected}", result["verdict"] == expected,
           detail=f"got={result['verdict']}: {result['message'][:70]}")


# ============================================================================
print()
print("=" * 78)
print("SECTION C — End-to-end file tests (shipped sample docs)")
print("=" * 78)

FILE_CASES = [
    ("SOP_Deviation_Latest.docx", "PASS"),
    ("SOP_Deviation_Outdated_Version.docx", "WARN"),
    ("SOP_Deviation_Superseded_Template.docx", "FAIL"),
    ("Form_Unknown_Template.docx", "FLAG"),
]
for filename, expected in FILE_CASES:
    path = os.path.join(SAMPLE_DIR, filename)
    result = check_document(path, MASTER_LIST)
    expect(f"{filename:<42} expected={expected}", result["verdict"] == expected,
           detail=f"got={result['verdict']}")


# ============================================================================
print()
print("=" * 78)
print("SECTION D — Edge cases found during stress-testing")
print("=" * 78)

# D1. Case sensitivity — lowercase Template ID in the footer must still match
r = check("v-qms-0114221", "3.0", master_df)
expect("Lowercase Template ID in footer still matches (case-insensitive)",
       r["verdict"] == "PASS", detail=r["verdict"])

# D2. Non-numeric version string (letter-based revision scheme) must not crash
try:
    r = check("V-QMS-0114221", "C", master_df)
    ok = r["verdict"] == "FLAG"
except Exception as e:
    ok = False
    r = {"message": f"CRASHED: {e}"}
expect("Non-numeric version ('Rev C' style) flags gracefully, doesn't crash",
       ok, detail=r.get("message", "")[:70])

# D3. Corrupt / non-docx file with a .docx extension must not crash
corrupt_path = fx.make_corrupt_docx()
r = extract(corrupt_path)
expect("Corrupt .docx file returns a graceful error, doesn't crash",
       r["error"] is not None and r["template_id"] is None, detail=str(r["error"])[:70])

# D4. Empty/zero-byte PDF must not crash
empty_pdf_path = fx.make_empty_pdf()
r = extract(empty_pdf_path)
expect("Empty/zero-byte PDF returns a graceful error, doesn't crash",
       r["error"] is not None, detail=str(r["error"])[:70])

# D5. Missing file path must not crash
r = extract("/tmp/this_file_does_not_exist_anywhere.docx")
expect("Nonexistent file path returns a graceful error, doesn't crash",
       r["error"] is not None)

# D6. Unsupported file extension
r = extract("/tmp/some_file.txt")
expect("Unsupported extension (.txt) returns a graceful error",
       r["error"] is not None)

# D7. Document with completely blank footer (no template stamped at all)
no_footer_path = fx.make_docx_no_footer("no_footer.docx")
result = check_document(no_footer_path, MASTER_LIST)
expect("Document with no footer at all -> FLAG (not a crash, not a false PASS)",
       result["verdict"] == "FLAG", detail=result["verdict"])

# D8. Footer text using 'Revision:' instead of 'Version:'
rev_path = fx.make_docx_with_footer("revision_wording.docx",
                                     "Template ID: V-QMS-0114221   Revision: 3.0")
r = extract(rev_path)
expect("'Revision:' wording (not just 'Version:') is correctly parsed",
       r["template_id"] == "V-QMS-0114221" and r["version"] == "3.0", detail=str(r))

# D9. Footer using 'Rev.' abbreviation with a period
rev2_path = fx.make_docx_with_footer("rev_abbrev.docx",
                                      "Doc ID: V-QMS-0114221 | Rev. 2.0")
r = extract(rev2_path)
expect("'Rev.' abbreviation with period is correctly parsed",
       r["template_id"] == "V-QMS-0114221" and r["version"] == "2.0", detail=str(r))

# D10. Footer laid out as a table (common in real controlled templates), not a paragraph
table_path = fx.make_docx_with_table_footer("table_footer.docx",
                                             ["Doc ID: V-QMS-0114221", "Version: 3.0"])
r = extract(table_path)
expect("Footer laid out as a table (not plain text) is still read correctly",
       r["template_id"] == "V-QMS-0114221" and r["version"] == "3.0", detail=str(r))

# D11. ALL CAPS footer text
caps_path = fx.make_docx_with_footer("all_caps.docx",
                                      "TEMPLATE ID: V-QMS-0114221 | VERSION: 3.0")
r = extract(caps_path)
expect("ALL CAPS footer text is correctly parsed",
       r["template_id"] == "V-QMS-0114221" and r["version"] == "3.0", detail=str(r))

# D12. Real OCR fallback on a genuinely scanned (image-only, no text layer) PDF
ocr_available = False
try:
    import pytesseract
    ocr_available = fx.check_tesseract_installed()
except ImportError:
    pass

scanned_pdf = fx.make_scanned_pdf_from_text("scanned_no_text_layer.pdf", "V-QMS-0114221", "3.0")

if ocr_available:
    try:
        import pdfplumber
        with pdfplumber.open(scanned_pdf) as pdf:
            has_text = bool(pdf.pages[0].extract_text())

        r = extract(scanned_pdf)
        ok = (not has_text) and r["template_id"] == "V-QMS-0114221" and r["version"] == "3.0"
        detail = f"has_text_layer={has_text}, extracted={r['template_id']}/{r['version']}"
    except Exception as e:
        ok = False
        detail = f"CRASHED: {e}"
    expect("Real OCR fallback correctly reads a genuinely scanned (image-only) PDF",
           ok, detail=detail)
else:
    print("[SKIP] Real OCR fallback correctly reads a genuinely scanned (image-only) PDF (pytesseract or tesseract binary not available)")
    # Test that we fallback gracefully and report the missing OCR dependencies
    r = extract(scanned_pdf)
    ok = r["template_id"] is None and r["error"] is None and "[OCR unavailable" in r["raw_footer"]
    expect("OCR fallback returns graceful error message when dependencies are missing", ok, detail=str(r))

# D13. PDF end-to-end for all 4 verdict types (not just docx)
try:
    all_ok = True
    for filename, expected in FILE_CASES:
        if filename == "SOP_Deviation_Latest.docx":
            pdf_path = fx.make_pdf_with_footer("SOP_Deviation_Latest.pdf", "V-QMS-0114221", "3.0")
        elif filename == "SOP_Deviation_Outdated_Version.docx":
            pdf_path = fx.make_pdf_with_footer("SOP_Deviation_Outdated_Version.pdf", "V-QMS-0114221", "2.0")
        elif filename == "SOP_Deviation_Superseded_Template.docx":
            pdf_path = fx.make_pdf_with_footer("SOP_Deviation_Superseded_Template.pdf", "V-QMS-0114100", "2.0")
        else:
            pdf_path = fx.make_pdf_with_footer("Form_Unknown_Template.pdf", "V-QMS-9999999", "1.0")

        result = check_document(pdf_path, MASTER_LIST)
        if result["verdict"] != expected:
            all_ok = False
            print(f"Failed for {filename}: expected {expected}, got {result['verdict']}")
except Exception as e:
    all_ok = False
    print(f"Exception in PDF end-to-end: {e}")
expect("PDF version of all 4 sample docs produces the same verdicts as docx",
       all_ok)

# D14. Master list with a non-numeric Latest_Version doesn't crash the checker
bad_master = master_df.copy()
bad_master["Latest_Version"] = bad_master["Latest_Version"].astype(object)
bad_master.loc["V-QMS-0114221", "Latest_Version"] = "N/A"
try:
    r = check("V-QMS-0114221", "3.0", bad_master)
    ok = r["verdict"] == "FLAG"
except Exception as e:
    ok = False
expect("Non-numeric Latest_Version in master list flags gracefully, doesn't crash", ok)

# Cleanup fixtures
fx.cleanup()

# ============================================================================
print()
print("=" * 78)
print(f"RESULT: {passed} passed, {failed} failed, {passed + failed} total")
if failures:
    print("Failed cases:")
    for f in failures:
        print(f"  - {f}")
print("=" * 78)

sys.exit(0 if failed == 0 else 1)
