"""
app.py
------
Streamlit web app — Pro Talent CV Formatter.

Fully branded UI version with:
- Custom top-nav header (PT logo, brand name, status pill, sign out)
- Red accent stripe under the header
- Blue info banner for active template
- Two-column upload + batch stats layout
- Custom result cards with status accent bars and avatar circles
- Branded login screen with the same visual language

Backend behaviour unchanged from earlier deployments.
"""

import io
import os
import zipfile
import base64
from pathlib import Path
import tempfile
import traceback

import streamlit as st
from dotenv import load_dotenv

from cv_parser import extract_cv_text
from ai_extractor import extract_candidate_info
from template_filler import fill_template, make_safe_filename

load_dotenv()

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent
DEFAULT_TEMPLATE = PROJECT_ROOT / "templates" / "pro_talent_template.docx"
LOGO_PATH = PROJECT_ROOT / "assets" / "pro_talent_logo.png"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Brand palette
PT_RED = "#C8102E"
PT_BLUE = "#185FA5"
PT_BLUE_LIGHT = "#EFF6FF"
PT_BLUE_BORDER = "#DBEAFE"
PT_TEXT = "#1F2937"
PT_TEXT_MUTED = "#6B7280"
PT_TEXT_FAINT = "#9CA3AF"
PT_BORDER = "#E5E7EB"
PT_SURFACE = "#F5F7FA"
PT_GREEN = "#1D9E75"
PT_AMBER = "#854F0B"
PT_AMBER_BG = "#FEF3C7"
PT_AMBER_BORDER = "#FCD34D"


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Pro Talent · CV Formatter",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Logo helper
# ---------------------------------------------------------------------------

def _logo_data_uri() -> str:
    if not LOGO_PATH.exists():
        return ""
    with open(LOGO_PATH, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


LOGO_SRC = _logo_data_uri()


# ---------------------------------------------------------------------------
# Custom CSS — heavy styling to override Streamlit's defaults
# ---------------------------------------------------------------------------

CUSTOM_CSS = f"""
<style>
    /* === Page chrome reset === */
    .block-container {{
        padding: 1.25rem 2rem 3rem !important;
        max-width: 1100px !important;
    }}

    /* Hide default streamlit chrome we don't want */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ background: transparent; }}

    /* === Branded header bar === */
    .pt-header-card {{
        background: white;
        border: 1px solid {PT_BORDER};
        border-bottom: 3px solid {PT_RED};
        border-radius: 10px 10px 0 0;
        padding: 14px 22px;
        display: flex;
        align-items: center;
        gap: 14px;
    }}
    .pt-header-card img {{
        width: 44px;
        height: 44px;
        border-radius: 8px;
        flex-shrink: 0;
    }}
    .pt-header-text {{ flex: 1; min-width: 0; }}
    .pt-header-name {{
        font-size: 16px;
        font-weight: 600;
        color: {PT_TEXT};
        line-height: 1.2;
        margin: 0;
    }}
    .pt-header-tagline {{
        font-size: 12px;
        color: {PT_TEXT_MUTED};
        margin: 2px 0 0;
    }}
    .pt-status-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        background: {PT_SURFACE};
        border-radius: 999px;
        font-size: 12px;
        color: {PT_TEXT_MUTED};
    }}
    .pt-status-dot {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: {PT_GREEN};
    }}

    /* === Info banner === */
    .pt-info-banner {{
        background: {PT_BLUE_LIGHT};
        border: 1px solid {PT_BLUE_BORDER};
        border-top: 0;
        padding: 9px 22px;
        font-size: 12px;
        color: #0C447C;
        border-radius: 0 0 10px 10px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .pt-info-banner svg {{ flex-shrink: 0; }}

    /* === Page title === */
    .pt-page-title {{
        font-size: 22px;
        font-weight: 600;
        color: {PT_TEXT};
        margin: 0 0 4px;
        letter-spacing: -0.01em;
    }}
    .pt-page-subtitle {{
        font-size: 13px;
        color: {PT_TEXT_MUTED};
        margin: 0 0 20px;
    }}

    /* === Two-column upload + stats === */
    .pt-twocol {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 22px;
    }}

    /* Upload zone */
    .pt-upload-zone {{
        background: white;
        border: 1.5px dashed #CBD5E1;
        border-radius: 12px;
        padding: 28px 20px;
        text-align: center;
    }}
    .pt-upload-icon {{
        width: 36px;
        height: 36px;
        margin: 0 auto 10px;
        background: {PT_RED};
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .pt-upload-title {{
        font-size: 13px;
        font-weight: 600;
        color: {PT_TEXT};
        margin: 0 0 2px;
    }}
    .pt-upload-hint {{
        font-size: 11px;
        color: {PT_TEXT_MUTED};
        margin: 0;
    }}

    /* Stats panel */
    .pt-stats-panel {{
        background: {PT_SURFACE};
        border-radius: 12px;
        padding: 18px 20px;
    }}
    .pt-stats-label {{
        font-size: 11px;
        font-weight: 600;
        color: {PT_TEXT_MUTED};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0 0 12px;
    }}
    .pt-stats-row {{
        display: flex;
        gap: 18px;
        align-items: stretch;
    }}
    .pt-stat {{ flex: 1; }}
    .pt-stat-value {{
        font-size: 22px;
        font-weight: 600;
        line-height: 1;
        color: {PT_TEXT};
    }}
    .pt-stat-value--green {{ color: {PT_GREEN}; }}
    .pt-stat-value--blue {{ color: {PT_BLUE}; }}
    .pt-stat-label {{
        font-size: 11px;
        color: {PT_TEXT_MUTED};
        margin-top: 4px;
    }}
    .pt-stats-divider {{
        width: 1px;
        background: {PT_BORDER};
    }}

    /* === Section labels === */
    .pt-label {{
        font-size: 11px;
        font-weight: 600;
        color: {PT_TEXT_MUTED};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 16px 0 10px;
    }}

    /* === Result cards === */
    .pt-card {{
        background: white;
        border: 1px solid {PT_BORDER};
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .pt-card-bar {{
        width: 4px;
        height: 36px;
        border-radius: 2px;
        flex-shrink: 0;
    }}
    .pt-card-bar--success {{ background: {PT_GREEN}; }}
    .pt-card-bar--neutral {{ background: {PT_BORDER}; }}
    .pt-avatar {{
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: {PT_BLUE_LIGHT};
        color: {PT_BLUE};
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 600;
        flex-shrink: 0;
    }}
    .pt-card-text {{ flex: 1; min-width: 0; }}
    .pt-card-name {{
        font-size: 13px;
        font-weight: 600;
        color: {PT_TEXT};
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .pt-card-meta {{
        font-size: 11px;
        color: {PT_TEXT_MUTED};
        margin: 1px 0 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    /* === Warning callout for fields-to-confirm === */
    .pt-warning {{
        background: {PT_AMBER_BG};
        border: 1px solid {PT_AMBER_BORDER};
        border-radius: 8px;
        padding: 10px 14px;
        margin: 8px 0 14px;
        display: flex;
        gap: 10px;
        align-items: flex-start;
    }}
    .pt-warning-title {{
        font-size: 12px;
        font-weight: 600;
        color: {PT_AMBER};
        margin: 0 0 2px;
    }}
    .pt-warning-body {{
        font-size: 11px;
        color: {PT_AMBER};
        margin: 0;
    }}

    /* === Override Streamlit's button styling === */
    .stButton > button {{
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 13px !important;
        padding: 8px 16px !important;
        transition: all 0.15s ease !important;
    }}
    .stButton > button[kind="primary"] {{
        background: {PT_RED} !important;
        border: 1px solid {PT_RED} !important;
        color: white !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background: #A30D24 !important;
        border-color: #A30D24 !important;
    }}
    .stDownloadButton > button {{
        border-radius: 8px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }}
    .stDownloadButton > button[kind="primary"] {{
        background: {PT_RED} !important;
        border: 1px solid {PT_RED} !important;
        color: white !important;
    }}
    .stDownloadButton > button[kind="primary"]:hover {{
        background: #A30D24 !important;
        border-color: #A30D24 !important;
    }}

    /* Streamlit's progress bar in red */
    .stProgress > div > div > div > div {{
        background: {PT_RED} !important;
    }}

    /* Tame the file uploader's appearance to match our style */
    [data-testid="stFileUploader"] section {{
        border: 1.5px dashed #CBD5E1 !important;
        border-radius: 12px !important;
        background: white !important;
    }}
    [data-testid="stFileUploader"] section:hover {{
        border-color: {PT_RED} !important;
        background: #FEF7F8 !important;
    }}

    /* Sidebar styling */
    section[data-testid="stSidebar"] {{
        background: {PT_SURFACE};
        border-right: 1px solid {PT_BORDER};
    }}

    /* === Login screen === */
    .pt-login {{
        max-width: 400px;
        margin: 60px auto 0;
        text-align: center;
    }}
    .pt-login img {{
        width: 72px;
        height: 72px;
        border-radius: 14px;
        margin-bottom: 18px;
    }}
    .pt-login h1 {{
        font-size: 24px;
        font-weight: 600;
        color: {PT_TEXT};
        margin: 0 0 6px;
        letter-spacing: -0.01em;
    }}
    .pt-login p {{
        font-size: 13px;
        color: {PT_TEXT_MUTED};
        margin: 0 0 24px;
    }}

    /* === Footer === */
    .pt-footer {{
        text-align: center;
        font-size: 11px;
        color: {PT_TEXT_FAINT};
        margin-top: 40px;
        padding-top: 18px;
        border-top: 1px solid #F3F4F6;
    }}

    /* Hide the file uploader label since we have our own */
    [data-testid="stFileUploaderDropzoneInstructions"] {{
        font-size: 12px !important;
    }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Password gate
# ---------------------------------------------------------------------------

def check_password() -> bool:
    """Show branded login screen until correct password entered."""

    expected_password = os.getenv("APP_PASSWORD")

    if not expected_password:
        return True  # No password configured (local dev)

    if st.session_state.get("authenticated"):
        return True

    logo_html = f'<img src="{LOGO_SRC}" alt="Pro Talent">' if LOGO_SRC else ""

    st.markdown(
        f"""
        <div class="pt-login">
            {logo_html}
            <h1>Pro Talent CV Formatter</h1>
            <p>Sign in with the team password to continue</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.form("login_form"):
            entered = st.text_input(
                "Team password",
                type="password",
                label_visibility="collapsed",
                placeholder="Team password",
            )
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

            if submitted:
                if entered == expected_password:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Please try again.")

        st.markdown(
            f'<p style="text-align: center; font-size: 11px; color: {PT_TEXT_FAINT}; margin-top: 16px;">'
            "For Pro Talent / Pro Appointments use only. "
            "Contact your team lead if you don't have the password."
            "</p>",
            unsafe_allow_html=True,
        )

    return False


if not check_password():
    st.stop()


# ---------------------------------------------------------------------------
# API key check
# ---------------------------------------------------------------------------

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    st.error(
        "Server configuration error: ANTHROPIC_API_KEY is not set. "
        "If you're an admin, set this environment variable in your hosting platform."
    )
    st.stop()


# ---------------------------------------------------------------------------
# Branded header
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <div class="pt-header-card">
        <img src="{LOGO_SRC}" alt="Pro Talent">
        <div class="pt-header-text">
            <p class="pt-header-name">Pro Talent</p>
            <p class="pt-header-tagline">Candidate profile generator</p>
        </div>
        <div class="pt-status-pill">
            <span class="pt-status-dot"></span>
            <span>Connected</span>
        </div>
    </div>
    <div class="pt-info-banner">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="7" stroke="#185FA5" stroke-width="1.3"/>
            <path d="M8 5v3.5M8 11v0.5" stroke="#185FA5" stroke-width="1.3" stroke-linecap="round"/>
        </svg>
        <span>Using <strong>Default Pro Talent</strong> template — upload a custom one in the sidebar if needed</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown('<p class="pt-label" style="margin-top: 0;">Template</p>', unsafe_allow_html=True)
    custom_template = st.file_uploader(
        "Custom template",
        type=["docx"],
        help="Optional. Upload your own .docx template with {{placeholder}} tokens.",
        label_visibility="collapsed",
    )
    if custom_template:
        st.success("Custom template loaded")
    else:
        st.caption("Using default Pro Talent template")

    st.divider()

    st.markdown('<p class="pt-label" style="margin-top: 0;">Quick tips</p>', unsafe_allow_html=True)
    st.caption("• Up to 20 CVs per batch")
    st.caption("• PDF and DOCX supported")
    st.caption("• Always review before sending")

    st.divider()

    if st.button("Sign out", use_container_width=True):
        st.session_state.pop("authenticated", None)
        st.rerun()


# ---------------------------------------------------------------------------
# Page title
# ---------------------------------------------------------------------------

st.markdown(
    """
    <h1 class="pt-page-title">Process candidate CVs</h1>
    <p class="pt-page-subtitle">Upload PDFs or Word documents — we'll fill the Pro Talent template and have profiles ready in seconds.</p>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Two-column upload + stats
# ---------------------------------------------------------------------------

# Read the current batch state
batch_count = len(st.session_state.get("uploaded_files", []))
processed_count = st.session_state.get("processed_count", 0)

col_upload, col_stats = st.columns([1, 1])

with col_upload:
    uploaded_cvs = st.file_uploader(
        "Drop CVs here",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        help="PDF or DOCX, up to 20 files at a time",
        label_visibility="collapsed",
    )

with col_stats:
    files_count = len(uploaded_cvs) if uploaded_cvs else 0
    st.markdown(
        f"""
        <div class="pt-stats-panel">
            <p class="pt-stats-label">This batch</p>
            <div class="pt-stats-row">
                <div class="pt-stat">
                    <div class="pt-stat-value">{files_count}</div>
                    <div class="pt-stat-label">Files queued</div>
                </div>
                <div class="pt-stats-divider"></div>
                <div class="pt-stat">
                    <div class="pt-stat-value pt-stat-value--green">{processed_count}</div>
                    <div class="pt-stat-label">Processed</div>
                </div>
                <div class="pt-stats-divider"></div>
                <div class="pt-stat">
                    <div class="pt-stat-value pt-stat-value--blue">~10s</div>
                    <div class="pt-stat-label">Per CV</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Action buttons
# ---------------------------------------------------------------------------

col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 6])
with col_btn1:
    process_clicked = st.button(
        "Process all CVs",
        type="primary",
        disabled=not uploaded_cvs,
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Processing logic (unchanged backend)
# ---------------------------------------------------------------------------

def resolve_template_path() -> Path:
    if custom_template:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp.write(custom_template.getvalue())
        tmp.close()
        return Path(tmp.name)
    return DEFAULT_TEMPLATE


def initials_from(name: str) -> str:
    parts = name.strip().split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


if process_clicked and uploaded_cvs:
    template_path = resolve_template_path()

    if not template_path.exists():
        st.error(f"Template not found at {template_path}.")
        st.stop()

    results = []
    progress = st.progress(0, text="Starting…")

    for i, cv_file in enumerate(uploaded_cvs):
        progress.progress(
            i / len(uploaded_cvs),
            text=f"Processing {cv_file.name} ({i + 1} of {len(uploaded_cvs)})"
        )

        try:
            tmp_cv = tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(cv_file.name).suffix
            )
            tmp_cv.write(cv_file.getvalue())
            tmp_cv.close()

            cv_text = extract_cv_text(tmp_cv.name)
            data = extract_candidate_info(cv_text, api_key=api_key)

            full_name = f"{data.get('first_name', '')} {data.get('surname', '')}".strip()
            safe_name = make_safe_filename(full_name or "candidate")
            output_path = OUTPUT_DIR / f"{safe_name}_profile.docx"
            counter = 1
            while output_path.exists():
                output_path = OUTPUT_DIR / f"{safe_name}_profile_{counter}.docx"
                counter += 1

            fill_template(template_path, data, output_path)
            results.append((cv_file.name, output_path, data, None))

        except Exception as e:
            results.append((cv_file.name, None, None, f"{type(e).__name__}: {e}"))
            print(traceback.format_exc())

    progress.progress(1.0, text="Done")
    st.session_state["processed_count"] = len([r for r in results if r[3] is None])

    # Store results in session state so they persist
    st.session_state["last_results"] = results


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

results = st.session_state.get("last_results", [])

if results:
    st.markdown('<p class="pt-label">Results</p>', unsafe_allow_html=True)

    successes = [r for r in results if r[3] is None]
    failures = [r for r in results if r[3] is not None]

    if successes:
        # Download-all button
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for _, output_path, _, _ in successes:
                zf.write(output_path, arcname=output_path.name)

        col_dl, _ = st.columns([2, 8])
        with col_dl:
            st.download_button(
                label=f"Download all {len(successes)} (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="candidate_profiles.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True,
            )

        st.write("")  # tiny spacer

        # Individual cards
        for cv_name, output_path, data, _ in successes:
            full_name = f"{data.get('first_name', '')} {data.get('surname', '')}".strip()
            display_name = full_name or "Candidate"
            initials = initials_from(display_name)

            # Build meta line: "From <file> · <position> · <location>"
            meta_parts = [f"From {cv_name}"]
            jobs = data.get("employment_history", [])
            if isinstance(jobs, list) and jobs and isinstance(jobs[0], dict):
                pos = jobs[0].get("position", "").strip()
                if pos and "(info absent" not in pos:
                    meta_parts.append(pos)
            location = data.get("residential_area", "").strip()
            if location and "(info absent" not in location:
                meta_parts.append(location)
            meta_line = " · ".join(meta_parts)

            # Card layout: HTML for visuals, Streamlit columns for the download button
            card_col, btn_col = st.columns([5, 1])
            with card_col:
                st.markdown(
                    f"""
                    <div class="pt-card">
                        <div class="pt-card-bar pt-card-bar--success"></div>
                        <div class="pt-avatar">{initials}</div>
                        <div class="pt-card-text">
                            <p class="pt-card-name">{display_name}</p>
                            <p class="pt-card-meta">{meta_line}</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with btn_col:
                with open(output_path, "rb") as f:
                    st.download_button(
                        label="Download",
                        data=f.read(),
                        file_name=output_path.name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"dl_{output_path.name}",
                        use_container_width=True,
                    )

            # Fields-to-confirm warning if applicable
            fields_to_confirm = []
            for field in ("identity_number", "equity", "transport", "current_salary", "required_salary", "availability"):
                if "(info absent on CV)" in str(data.get(field, "")):
                    fields_to_confirm.append(field.replace("_", " ").title())

            if fields_to_confirm:
                st.markdown(
                    f"""
                    <div class="pt-warning">
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" style="flex-shrink: 0; margin-top: 1px;">
                            <path d="M8 1L15 14H1L8 1Z" stroke="{PT_AMBER}" stroke-width="1.3" stroke-linejoin="round"/>
                            <path d="M8 6v3M8 11v0.5" stroke="{PT_AMBER}" stroke-width="1.3" stroke-linecap="round"/>
                        </svg>
                        <div>
                            <p class="pt-warning-title">Fields to confirm with candidate</p>
                            <p class="pt-warning-body">{" · ".join(fields_to_confirm)}</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("View full extraction"):
                st.json(data)

    if failures:
        st.markdown('<p class="pt-label">Failed</p>', unsafe_allow_html=True)
        for cv_name, _, _, error in failures:
            st.error(f"{cv_name} — {error}")


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="pt-footer">
        Pro Talent · Pro Appointments — Always review filled profiles before sending to clients
    </div>
    """,
    unsafe_allow_html=True,
)
