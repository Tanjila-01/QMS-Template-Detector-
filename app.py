import streamlit as st
import pandas as pd
import tempfile
import os
import sys
import textwrap

# Configure script path inserting for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor import extract
from checker import load_master_list, check

# Set layout configurations
st.set_page_config(page_title="Alcon QMS Template Detector", page_icon="📋", layout="wide")

# Inject premium custom CSS styles (fonts, grids, glassmorphism containers, badges)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Typography overrides */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header styling banner */
    .header-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    }
    .header-title {
        font-size: 2.25rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.025em;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .header-subtitle {
        color: #94a3b8;
        margin-top: 0.5rem;
        font-size: 1.05rem;
        font-weight: 400;
        margin-bottom: 0;
    }
    
    /* Card design system */
    .qms-card {
        background-color: white;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
    }
    
    /* Verdict cards with HSL high contrast borders */
    .verdict-card {
        padding: 1.25rem 1.5rem;
        border-radius: 10px;
        margin-top: 1rem;
        margin-bottom: 1.5rem;
        font-size: 1rem;
        font-weight: 500;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        border-left: 5px solid;
    }
    .verdict-pass {
        background-color: #f0fdf4;
        color: #166534;
        border-color: #bbf7d0;
        border-left-color: #166534;
    }
    .verdict-warn {
        background-color: #fffbeb;
        color: #92400e;
        border-color: #fde68a;
        border-left-color: #d97706;
    }
    .verdict-fail {
        background-color: #fef2f2;
        color: #991b1b;
        border-color: #fecaca;
        border-left-color: #dc2626;
    }
    .verdict-flag {
        background-color: #f8fafc;
        color: #334155;
        border-color: #e2e8f0;
        border-left-color: #64748b;
    }
    .verdict-title {
        font-size: 1.15rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Micro badges for comparative grids */
    .verdict-badge {
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
    }
    .badge-pass { background-color: #dcfce7; color: #15803d; }
    .badge-warn { background-color: #fef3c7; color: #b45309; }
    .badge-fail { background-color: #fee2e2; color: #b91c1c; }
    .badge-flag { background-color: #f1f5f9; color: #475569; }
    
    /* Guide Card inside Sidebar */
    .guide-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px;
        font-size: 0.85rem;
        line-height: 1.4;
        color: #334155;
        margin-top: 15px;
    }
    .guide-title {
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Cached extraction function to prevent sluggish re-runs
@st.cache_data(show_spinner=False)
def cached_extract(file_bytes: bytes, file_name: str) -> dict:
    """Writes bytes to a temp file, extracts metadata, and removes the temp file.
    Cached by file contents and name to prevent slow extraction on script re-run.
    """
    suffix = os.path.splitext(file_name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        doc_path = tmp.name
    try:
        result = extract(doc_path)
    finally:
        if os.path.exists(doc_path):
            os.unlink(doc_path)
    return result

# Header Banner
st.markdown(
    """
    <div class="header-container">
        <h1 class="header-title">📋 Alcon QMS Template Detector</h1>
        <p class="header-subtitle">Verify controlled documents (SOPs, Reports, Protocols, Forms) against active Quality Management System template versions before submission.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ QMS Registry Config")
    default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "master_list.xlsx")
    master_file = st.file_uploader("Upload active master list (.xlsx)", type=["xlsx"])
    
    if master_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(master_file.read())
            master_path = tmp.name
        st.success("Custom registry uploaded.")
    else:
        master_path = default_path
        st.info("Using default template registry.")
    
    # Robust registry load with clean fallback to default registry if parsing error occurs
    try:
        master_df = load_master_list(master_path)
    except Exception as e:
        st.error(f"Error loading custom registry: {e}")
        st.info("Falling back to default QMS registry.")
        master_df = load_master_list(default_path)
        
    # QMS Guide Box
    st.markdown(
        """
        <div class="guide-box">
            <div class="guide-title">Compliance Action Guide</div>
            <b>✅ PASS</b>: The template is active and uses the latest approved version.<br><br>
            <b>⚠️ WARN</b>: The template is active, but a newer approved version is available in the QMS.<br><br>
            <b>❌ FAIL</b>: The template has been superseded or withdrawn. Rework is required.<br><br>
            <b>❓ FLAG</b>: The template ID was not found or the document structure is missing stamp tags.
        </div>
        """,
        unsafe_allow_html=True,
    )

# Setup Main Tabs
tab1, tab2, tab3 = st.tabs(["🔍 Single Validator", "📦 Batch Checker", "🗂️ QMS Master Registry"])

# Tab 1: Single Document Validator
with tab1:
    st.subheader("🔍 Scan Single Document")
    st.caption("Upload a single Word (.docx) or PDF (.pdf) file to analyze its footer stamp.")
    
    single_uploaded = st.file_uploader("Drag and drop your file here", type=["docx", "pdf"], key="single_uploader")
    
    if single_uploaded:
        file_bytes = single_uploaded.getvalue()
        with st.spinner("Extracting template markers..."):
            extraction = cached_extract(file_bytes, single_uploaded.name)
            
        if extraction["error"]:
            result = {
                "verdict": "FLAG",
                "message": f"Parsing Error: {extraction['error']}",
                "matched_row": None
            }
        else:
            result = check(extraction["template_id"], extraction["version"], master_df)
            
        # Display Result Card
        VERDICT_CARD_STYLE = {
            "PASS": ("verdict-pass", "✅ Approved Template Version"),
            "WARN": ("verdict-warn", "⚠️ Outdated Template Version"),
            "FAIL": ("verdict-fail", "❌ Non-Compliant Template Status"),
            "FLAG": ("verdict-flag", "❓ Warning / Unrecognized Footer"),
        }
        
        card_class, header_title = VERDICT_CARD_STYLE[result["verdict"]]
        
        st.markdown(
            f"""
            <div class="verdict-card {card_class}">
                <div class="verdict-title">{header_title}</div>
                <div>{result['message']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # Details layout
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("📝 Extracted Stamp Metadata", expanded=True):
                st.write(f"**Filename:** `{single_uploaded.name}`")
                st.write(f"**Extracted Template ID:** `{extraction['template_id'] or 'Not Detected'}`")
                st.write(f"**Extracted Version:** `{extraction['version'] or 'Not Detected'}`")
                st.text_area("Raw Footer Text", extraction["raw_footer"] or "No footer text extracted.", height=100)
                
        with col2:
            if result.get("matched_row"):
                with st.expander("📋 QMS Registry Reference Match", expanded=True):
                    row = result["matched_row"]
                    st.json(row)
            else:
                with st.expander("📋 QMS Registry Reference Match", expanded=True):
                    st.warning("No matching Template ID found in the current master registry.")
    else:
        st.info("Upload a document above to verify compliance status.")

# Tab 2: Batch Checker
with tab2:
    st.subheader("📦 Bulk Package Validator")
    st.caption("Upload multiple Word and PDF files to validate an entire document release package.")
    
    batch_uploaded = st.file_uploader(
        "Upload files (.docx, .pdf)",
        type=["docx", "pdf"],
        accept_multiple_files=True,
        key="batch_uploader"
    )
    
    if batch_uploaded:
        results = []
        progress_bar = st.progress(0)
        
        for idx, f in enumerate(batch_uploaded):
            file_bytes = f.getvalue()
            # Fast extraction via cache
            extraction = cached_extract(file_bytes, f.name)
            
            if extraction["error"]:
                res = {
                    "File Name": f.name,
                    "Template ID": "N/A",
                    "Version": "N/A",
                    "Verdict": "FLAG",
                    "Details": extraction["error"]
                }
            else:
                check_res = check(extraction["template_id"], extraction["version"], master_df)
                res = {
                    "File Name": f.name,
                    "Template ID": extraction["template_id"] or "Not Found",
                    "Version": extraction["version"] or "Not Found",
                    "Verdict": check_res["verdict"],
                    "Details": check_res["message"]
                }
            results.append(res)
            progress_bar.progress((idx + 1) / len(batch_uploaded))
        progress_bar.empty()
            
        df_results = pd.DataFrame(results)
        
        # Summary statistics
        total_files = len(df_results)
        pass_c = len(df_results[df_results["Verdict"] == "PASS"])
        warn_c = len(df_results[df_results["Verdict"] == "WARN"])
        fail_c = len(df_results[df_results["Verdict"] == "FAIL"])
        flag_c = len(df_results[df_results["Verdict"] == "FLAG"])
        
        # Single horizontal metrics bar with color-coded counts
        metrics_html = textwrap.dedent(f"""
        <div style="background-color: var(--background-color-secondary); padding: 12px 20px; border-radius: 8px; border: 1px solid var(--border-color); display: flex; gap: 2rem; align-items: center; justify-content: flex-start; flex-wrap: wrap; margin-bottom: 1.5rem; font-weight: 500; font-size: 0.95rem;">
            <div style="color: var(--text-color); display: flex; align-items: center; gap: 6px;">📁 Total Documents: <strong style="font-size: 1.1rem; color: var(--text-color);">{total_files}</strong></div>
            <div style="color: var(--text-color); display: flex; align-items: center; gap: 6px;">🟢 Pass: <strong style="font-size: 1.1rem; color: #15803d;">{pass_c}</strong></div>
            <div style="color: var(--text-color); display: flex; align-items: center; gap: 6px;">🟡 Warning: <strong style="font-size: 1.1rem; color: #d97706;">{warn_c}</strong></div>
            <div style="color: var(--text-color); display: flex; align-items: center; gap: 6px;">🔴 Failure: <strong style="font-size: 1.1rem; color: #dc2626;">{fail_c}</strong></div>
            <div style="color: var(--text-color); display: flex; align-items: center; gap: 6px;">⚪ Flagged: <strong style="font-size: 1.1rem; color: #64748b;">{flag_c}</strong></div>
        </div>
        """).strip()
        st.markdown(metrics_html, unsafe_allow_html=True)
        
        # Display the results table with HTML badges
        badge_style = {
            "PASS": "badge-pass",
            "WARN": "badge-warn",
            "FAIL": "badge-fail",
            "FLAG": "badge-flag",
        }
        
        # Theme-aware table headers and borders using CSS variables
        table_html = textwrap.dedent("""
        <table style="width:100%; border-collapse: collapse; margin-top: 10px;">
            <thead>
                <tr style="background-color: var(--background-color-secondary); border-bottom: 2px solid var(--border-color); text-align: left;">
                    <th style="padding: 12px; font-weight: 600; color: var(--text-color);">File Name</th>
                    <th style="padding: 12px; font-weight: 600; color: var(--text-color);">Template ID</th>
                    <th style="padding: 12px; font-weight: 600; color: var(--text-color);">Version</th>
                    <th style="padding: 12px; font-weight: 600; color: var(--text-color); text-align: center;">Verdict</th>
                    <th style="padding: 12px; font-weight: 600; color: var(--text-color);">Action Message Details</th>
                </tr>
            </thead>
            <tbody>
        """).strip()
        for index, row in df_results.iterrows():
            b_class = badge_style[row["Verdict"]]
            table_html += textwrap.dedent(f"""
            <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-color);">
                <td style="padding: 12px; font-weight: 500; color: var(--text-color);">{row['File Name']}</td>
                <td style="padding: 12px; font-family: monospace; font-size: 0.9em; color: var(--text-color);">{row['Template ID']}</td>
                <td style="padding: 12px; font-family: monospace; color: var(--text-color);">{row['Version']}</td>
                <td style="padding: 12px; text-align: center;">
                    <span class="verdict-badge {b_class}">{row['Verdict']}</span>
                </td>
                <td style="padding: 12px; font-size: 0.9em; color: var(--text-color);">{row['Details']}</td>
            </tr>
            """).strip()
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)
        
        # Download compliance report
        csv = df_results.to_csv(index=False).encode('utf-8')
        st.write("")
        st.download_button(
            label="📥 Download QMS Compliance Report (CSV)",
            data=csv,
            file_name="qms_compliance_report.csv",
            mime="text/csv",
            key="download_csv"
        )
    else:
        st.info("Upload multiple documents above to run batch validation.")

# Tab 3: Registry Search Catalog
with tab3:
    st.subheader("🗂️ QMS Master Template Catalog")
    st.caption("Search active template configurations registered in Alcon QMS.")
    
    # Search input
    search_query = st.text_input("🔍 Search templates by ID, Title, or Owner Department", "")
    
    reg_df = master_df.reset_index()
    if search_query:
        search_query_clean = search_query.strip().upper()
        # fillna("") prevents logic ValueError exceptions on NaN fields in custom databases
        mask = (
            reg_df["Template_ID"].fillna("").str.upper().str.contains(search_query_clean) |
            reg_df["Template_Name"].fillna("").str.upper().str.contains(search_query_clean) |
            reg_df["Owner_Department"].fillna("").str.upper().str.contains(search_query_clean)
        )
        filtered_df = reg_df[mask]
    else:
        filtered_df = reg_df
        
    # Metrics
    t_count = len(filtered_df)
    eff_count = len(filtered_df[filtered_df["Status"] == "Effective"])
    sup_count = len(filtered_df[filtered_df["Status"] == "Superseded"])
    with_count = len(filtered_df[filtered_df["Status"] == "Withdrawn"])
    
    # Single horizontal metrics bar with color-coded counts for catalog registry
    metrics_cat_html = textwrap.dedent(f"""
    <div style="background-color: var(--background-color-secondary); padding: 12px 20px; border-radius: 8px; border: 1px solid var(--border-color); display: flex; gap: 2rem; align-items: center; justify-content: flex-start; flex-wrap: wrap; margin-bottom: 1.5rem; font-weight: 500; font-size: 0.95rem;">
        <div style="color: var(--text-color); display: flex; align-items: center; gap: 6px;">📊 Catalog Size: <strong style="font-size: 1.1rem; color: var(--text-color);">{t_count}</strong></div>
        <div style="color: var(--text-color); display: flex; align-items: center; gap: 6px;">🟢 Effective: <strong style="font-size: 1.1rem; color: #15803d;">{eff_count}</strong></div>
        <div style="color: var(--text-color); display: flex; align-items: center; gap: 6px;">🟡 Superseded: <strong style="font-size: 1.1rem; color: #d97706;">{sup_count}</strong></div>
        <div style="color: var(--text-color); display: flex; align-items: center; gap: 6px;">🔴 Withdrawn: <strong style="font-size: 1.1rem; color: #dc2626;">{with_count}</strong></div>
    </div>
    """).strip()
    st.markdown(metrics_cat_html, unsafe_allow_html=True)
    
    # Custom Registry Display Table
    status_badge_style = {
        "Effective": "badge-pass",
        "Superseded": "badge-warn",
        "Withdrawn": "badge-fail",
    }
    
    cat_html = textwrap.dedent("""
    <table style="width:100%; border-collapse: collapse; margin-top: 10px;">
        <thead>
            <tr style="background-color: var(--background-color-secondary); border-bottom: 2px solid var(--border-color); text-align: left;">
                <th style="padding: 10px; font-weight: 600; color: var(--text-color);">Template ID</th>
                <th style="padding: 10px; font-weight: 600; color: var(--text-color);">Template Description / Name</th>
                <th style="padding: 10px; font-weight: 600; color: var(--text-color); text-align: center;">Latest Version</th>
                <th style="padding: 10px; font-weight: 600; color: var(--text-color); text-align: center;">Registry Status</th>
                <th style="padding: 10px; font-weight: 600; color: var(--text-color);">Owner Department</th>
            </tr>
        </thead>
        <tbody>
    """).strip()
    for index, row in filtered_df.iterrows():
        st_class = status_badge_style.get(row["Status"], "badge-flag")
        cat_html += textwrap.dedent(f"""
        <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-color);">
            <td style="padding: 10px; font-family: monospace; font-size: 0.9em; font-weight: 600; color: var(--text-color);">{row['Template_ID']}</td>
            <td style="padding: 10px; font-size: 0.9em; color: var(--text-color);">{row['Template_Name']}</td>
            <td style="padding: 10px; font-family: monospace; text-align: center; color: var(--text-color);">v{row['Latest_Version']}</td>
            <td style="padding: 10px; text-align: center;">
                <span class="verdict-badge {st_class}">{row['Status']}</span>
            </td>
            <td style="padding: 10px; font-size: 0.9em; color: var(--text-color);">{row['Owner_Department']}</td>
        </tr>
        """).strip()
    cat_html += "</tbody></table>"
    st.markdown(cat_html, unsafe_allow_html=True)

st.divider()
st.caption(
    "Compliance Note: Core logic remains fully deterministic (regular expression extraction + registry lookups) "
    "to ensure complete auditability and repeatability for medical device QA. Optional OCR fallback is provided only "
    "for flattened/scanned image documents that do not contain a native document text layer."
)
