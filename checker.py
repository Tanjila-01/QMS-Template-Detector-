"""
checker.py — looks up an extracted (template_id, version) against the master
list and returns one of 4 verdicts: PASS / WARN / FAIL / FLAG.

Pure function, no I/O side effects beyond reading the master list once —
this is the part a QA/validation team would unit test and sign off on.
"""
import pandas as pd

VERDICT_PASS = "PASS"
VERDICT_WARN = "WARN"
VERDICT_FAIL = "FAIL"
VERDICT_FLAG = "FLAG"


def load_master_list(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Master List")
    # Uppercase + strip Template_ID so lookups aren't broken by case differences
    # coming from OCR, manual typing, or inconsistent template stamping.
    df["Template_ID"] = df["Template_ID"].astype(str).str.strip().str.upper()
    df["Status"] = df["Status"].astype(str).str.strip().str.capitalize()
    df["Superseded_By"] = df["Superseded_By"].fillna("").astype(str).str.strip().str.upper()
    return df.set_index("Template_ID")


def check(template_id: str, version: str, master_df: pd.DataFrame) -> dict:
    """Returns a dict: verdict, message, and the matched master-list row (if any)."""
    if not template_id:
        return {
            "verdict": VERDICT_FLAG,
            "message": "Could not find a Template ID in the document footer. "
                       "Please verify this document uses a controlled QMS template.",
            "matched_row": None,
        }

    template_id = template_id.strip().upper()

    if template_id not in master_df.index:
        return {
            "verdict": VERDICT_FLAG,
            "message": f"Template ID '{template_id}' was not found in the master list. "
                       f"Contact QA to confirm whether this is a valid, currently registered template.",
            "matched_row": None,
        }

    row = master_df.loc[template_id]
    status = row["Status"]

    try:
        latest_version = float(row["Latest_Version"])
    except (TypeError, ValueError):
        return {
            "verdict": VERDICT_FLAG,
            "message": f"Master list has a non-numeric Latest_Version for {template_id} "
                       f"('{row['Latest_Version']}'). Please have QA correct the master list entry.",
            "matched_row": row.to_dict(),
        }

    doc_version = None
    if version:
        try:
            doc_version = float(version)
        except ValueError:
            return {
                "verdict": VERDICT_FLAG,
                "message": f"Found version '{version}' for {template_id}, but it isn't a numeric "
                           f"version (e.g. this template may use a letter-based revision scheme like "
                           f"'Rev C'). Please verify manually against the latest approved version "
                           f"(v{latest_version}).",
                "matched_row": row.to_dict(),
            }

    if status == "Withdrawn":
        return {
            "verdict": VERDICT_FAIL,
            "message": f"'{row['Template_Name']}' ({template_id}) was withdrawn on "
                       f"{row['Effective_Date']} and has no direct replacement. "
                       f"Contact QA for the current approved template for this document type.",
            "matched_row": row.to_dict(),
        }

    if status == "Superseded":
        return {
            "verdict": VERDICT_FAIL,
            "message": f"'{row['Template_Name']}' ({template_id}) was superseded on "
                       f"{row['Effective_Date']} by {row['Superseded_By']}. "
                       f"Please regenerate this document using the new template before submission.",
            "matched_row": row.to_dict(),
        }

    # status == Effective from here on
    if doc_version is None:
        return {
            "verdict": VERDICT_FLAG,
            "message": f"Template ID {template_id} is Effective, but no version number could be "
                       f"read from the footer. Please verify manually (latest is v{latest_version}).",
            "matched_row": row.to_dict(),
        }

    if doc_version < latest_version:
        return {
            "verdict": VERDICT_WARN,
            "message": f"'{row['Template_Name']}' ({template_id}) is on v{doc_version}, but "
                       f"v{latest_version} is the current approved version. "
                       f"Please update to the latest template before submitting for review.",
            "matched_row": row.to_dict(),
        }

    return {
        "verdict": VERDICT_PASS,
        "message": f"'{row['Template_Name']}' ({template_id}) v{doc_version} is the current "
                   f"approved template. Ready for submission.",
        "matched_row": row.to_dict(),
    }


def check_document(doc_path: str, master_list_path: str) -> dict:
    """Convenience wrapper: extract + check in one call."""
    from extractor import extract
    extraction = extract(doc_path)

    if extraction["error"]:
        # A real extraction failure (corrupt/missing/unsupported file) is a
        # different problem than "template ID not found" and should read that way.
        return {
            "verdict": VERDICT_FLAG,
            "message": extraction["error"],
            "matched_row": None,
            "extracted_template_id": None,
            "extracted_version": None,
            "raw_footer": None,
        }

    master_df = load_master_list(master_list_path)
    result = check(extraction["template_id"], extraction["version"], master_df)
    result["extracted_template_id"] = extraction["template_id"]
    result["extracted_version"] = extraction["version"]
    result["raw_footer"] = extraction["raw_footer"]
    return result


if __name__ == "__main__":
    import sys
    print(check_document(sys.argv[1], sys.argv[2]))
