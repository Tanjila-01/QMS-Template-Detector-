import streamlit as st
import pandas as pd
import tempfile, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor import extract
from checker import load_master_list, check

st.set_page_config(page_title="Outdated Template Detector", page_icon="📋", layout="centered")

VERDICT_STYLE = {
    "PASS": ("✅", "#1e7e34", "#d4edda"),
    "WARN": ("⚠️", "#856404", "#fff3cd"),
    "FAIL": ("❌", "#721c24", "#f8d7da"),
    "FLAG": ("❓", "#383d41", "#e2e3e5"),
}

st.title("📋 Outdated Template Detector")
st.caption("Checks whether a Word/PDF document uses the latest approved QMS template — before it goes to review.")

with st.sidebar:
    st.header("Master List")
    default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "master_list.xlsx")
    master_file = st.file_uploader("Upload master list (.xlsx)", type=["xlsx"])
    if master_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(master_file.read())
            master_path = tmp.name
        st.success("Using uploaded master list")
    else:
        master_path = default_path
        st.info("Using bundled sample master list")

    master_df = load_master_list(master_path)
    st.dataframe(master_df.reset_index()[["Template_ID", "Status", "Latest_Version"]], height=250, hide_index=True)

st.subheader("Check a document")
uploaded = st.file_uploader("Upload a .docx or .pdf", type=["docx", "pdf"])

if uploaded:
    suffix = os.path.splitext(uploaded.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        doc_path = tmp.name

    extraction = extract(doc_path)
    if extraction["error"]:
        result = {"verdict": "FLAG", "message": extraction["error"], "matched_row": None}
    else:
        result = check(extraction["template_id"], extraction["version"], master_df)

    icon, text_color, bg_color = VERDICT_STYLE[result["verdict"]]

    st.markdown(
        f"""
        <div style="background-color:{bg_color}; color:{text_color}; padding:16px 20px;
                    border-radius:8px; font-size:16px; margin-top:10px;">
            <b>{icon} {result['verdict']}</b><br>
            {result['message']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Extraction details (what the tool read from the footer)"):
        st.write(f"**File:** {uploaded.name}")
        st.write(f"**Extracted Template ID:** {extraction['template_id']}")
        st.write(f"**Extracted Version:** {extraction['version']}")
        st.text(f"Raw footer text:\n{extraction['raw_footer']}")

    if result.get("matched_row"):
        with st.expander("Matched master list row"):
            st.json(result["matched_row"])

    os.unlink(doc_path)
else:
    st.info("Upload a document above to check it against the master list.")

st.divider()
st.caption(
    "Core logic is deterministic (regex extraction + table lookup) — no AI is used for the "
    "pass/fail decision, which keeps it fully auditable for a regulated environment. "
    "AI/OCR would only assist with scanned documents that have no text layer."
)
