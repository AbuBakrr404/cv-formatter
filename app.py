"""
app.py
------
Streamlit web app — Pro Talent CV Formatter.

Stable basic-theming version:
- Pro Talent red primary colour
- PT logo in the page header
- Branded login screen
- Standard Streamlit components (no fragile custom HTML)
- File uploads and reruns work reliably
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
from supabase import create_client, Client

from cv_parser import extract_cv_text
from ai_extractor import extract_candidate_info
from template_filler import fill_template, make_safe_filename

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent
DEFAULT_TEMPLATE = PROJECT_ROOT / "templates" / "pro_talent_template.docx"
LOGO_PATH = PROJECT_ROOT / "assets" / "pro_talent_logo.png"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Pro Talent · CV Formatter",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "📄",
    layout="centered",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Light CSS — only colour tweaks, nothing that interferes with components
# ---------------------------------------------------------------------------

LIGHT_CSS = """
<style>
    .block-container { padding-top: 3rem; }
    .pt-header-row {
        display: flex;
        align-items: center;
        gap: 14px;
        padding-bottom: 12px;
        margin-bottom: 8px;
        border-bottom: 3px solid #C8102E;
    }
    .pt-header-row img {
        width: 44px;
        height: 44px;
        border-radius: 8px;
    }
    .pt-header-name {
        font-size: 18px;
        font-weight: 600;
        color: #1F2937;
        margin: 0;
        line-height: 1.2;
    }
    .pt-header-tagline {
        font-size: 12px;
        color: #6B7280;
        margin: 2px 0 0;
    }
    .pt-footer {
        text-align: center;
        font-size: 11px;
        color: #9CA3AF;
        margin-top: 32px;
        padding-top: 16px;
        border-top: 1px solid #F3F4F6;
    }
    .pt-login-wrap {
        max-width: 380px;
        margin: 50px auto 24px;
        text-align: center;
    }
    .pt-login-wrap img {
        width: 64px;
        height: 64px;
        border-radius: 12px;
        margin-bottom: 16px;
    }
    .pt-login-wrap h1 {
        font-size: 22px;
        font-weight: 600;
        color: #1F2937;
        margin: 0 0 6px;
    }
    .pt-login-wrap p {
        font-size: 13px;
        color: #6B7280;
        margin: 0 0 16px;
    }
   /* Sidebar arrows — make button visible and Pro Talent red */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    button[kind="header"],
    button[kind="headerNoPadding"] {
        background-color: #C8102E !important;
        border-radius: 6px !important;
        padding: 6px !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="collapsedControl"] svg,
    button[kind="header"] svg,
    button[kind="headerNoPadding"] svg,
    [data-testid="stSidebarCollapsedControl"] *,
    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="collapsedControl"] *,
    button[kind="header"] *,
    button[kind="headerNoPadding"] * {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }
    [data-testid="stSidebarCollapsedControl"]:hover,
    [data-testid="stSidebarCollapseButton"]:hover,
    [data-testid="collapsedControl"]:hover,
    button[kind="header"]:hover,
    button[kind="headerNoPadding"]:hover {
        background-color: #A00C24 !important;
}

</style>
"""

# Apply theme based on session state
_theme_choice = st.session_state.get("app_theme", "light")
DARK_OVERRIDE_CSS = """
<style>
    /* Page background and main text */
    body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #1F2937 !important;
        color: #F3F4F6 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #111827 !important;
    }
    .pt-header-name { color: #F3F4F6 !important; }
    .pt-header-tagline { color: #9CA3AF !important; }
    .pt-footer { color: #6B7280 !important; }
    .stMarkdown, .stText, label, p, h1, h2, h3, h4 {
        color: #F3F4F6 !important;
    }

    /* File uploader (the "Drop CVs here" + Upload button area) */
    [data-testid="stFileUploader"] section {
        background-color: #374151 !important;
        border: 1px dashed #6B7280 !important;
    }
    [data-testid="stFileUploader"] section button {
        background-color: #4B5563 !important;
        color: #F3F4F6 !important;
        border: 1px solid #6B7280 !important;
    }
    [data-testid="stFileUploader"] section button:hover {
        background-color: #6B7280 !important;
    }
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploaderDropzoneInstructions"] small,
    [data-testid="stFileUploaderDropzoneInstructions"] span,
    [data-testid="stFileUploaderDropzoneInstructions"] div {
        color: #F3F4F6 !important;
    }
    [data-testid="stFileUploaderFile"] {
        background-color: #374151 !important;
        color: #F3F4F6 !important;
    }

    /* Primary buttons (Process all CVs, Sign in, Download all) */
    .stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {
        background-color: #C8102E !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    .stButton button[kind="primary"]:hover, .stDownloadButton button[kind="primary"]:hover {
        background-color: #A00C24 !important;
    }

    /* Secondary buttons (Sign out, Clear results, theme toggle) */
    .stButton button:not([kind="primary"]), .stDownloadButton button:not([kind="primary"]) {
        background-color: #374151 !important;
        color: #F3F4F6 !important;
        border: 1px solid #4B5563 !important;
    }
    .stButton button:not([kind="primary"]):hover, .stDownloadButton button:not([kind="primary"]):hover {
        background-color: #4B5563 !important;
    }

    /* Disabled buttons */
    .stButton button:disabled, .stDownloadButton button:disabled {
        background-color: #1F2937 !important;
        color: #6B7280 !important;
        border: 1px solid #374151 !important;
    }

    /* Text inputs (login form) */
    [data-testid="stTextInput"] input {
        background-color: #374151 !important;
        color: #F3F4F6 !important;
        border: 1px solid #4B5563 !important;
    }
    /* Show/hide password eye icon button */
    [data-testid="stTextInput"] button {
        background-color: #4B5563 !important;
        color: #F3F4F6 !important;
        border: 1px solid #4B5563 !important;
    }
    [data-testid="stTextInput"] button:hover {
        background-color: #6B7280 !important;
    }
    [data-testid="stTextInput"] button svg {
        fill: #F3F4F6 !important;
        color: #F3F4F6 !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #9CA3AF !important;
        opacity: 1 !important;
    }
    [data-testid="stTextInput"] input::-webkit-input-placeholder {
        color: #9CA3AF !important;
        opacity: 1 !important;
    }

    /* Expander headers (candidate result cards) */
    [data-testid="stExpander"] {
        background-color: #1F2937 !important;
        border: 1px solid #374151 !important;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] details summary {
        color: #F3F4F6 !important;
        background-color: #374151 !important;
    }
    [data-testid="stExpander"] details {
        background-color: #1F2937 !important;
    }
    [data-testid="stExpanderToggleIcon"] {
        color: #F3F4F6 !important;
    }

    /* Success / warning / error message boxes */
    [data-testid="stAlert"] {
        background-color: #374151 !important;
    }

    /* Captions and small grey text */
    [data-testid="stCaptionContainer"], .stCaption {
        color: #9CA3AF !important;
    }
   /* Sidebar arrows — aggressive targeting to catch all Streamlit versions */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"],
    [data-testid="stSidebarHeader"] button,
    [data-testid="stHeader"] button,
    [class*="SidebarCollapse"],
    [class*="collapsedControl"],
    button[kind="headerNoPadding"] {
        background-color: #4B5563 !important;
        border: 1px solid #6B7280 !important;
        border-radius: 6px !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    [data-testid="stSidebarCollapsedControl"] *,
    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="collapsedControl"] *,
    [data-testid="stSidebarHeader"] button *,
    [data-testid="stHeader"] button *,
    [class*="SidebarCollapse"] *,
    [class*="collapsedControl"] *,
    button[kind="headerNoPadding"] * {
        fill: #C8102E !important;
        color: #C8102E !important;
        stroke: #C8102E !important;
        opacity: 1 !important;
    }
    </style>
"""
st.markdown(LIGHT_CSS, unsafe_allow_html=True)
if _theme_choice == "dark":
    st.markdown(DARK_OVERRIDE_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Logo helper
# ---------------------------------------------------------------------------

def _logo_data_uri() -> str:
    if not LOGO_PATH.exists():
        return ""
    with open(LOGO_PATH, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"


LOGO_SRC = _logo_data_uri()


# ---------------------------------------------------------------------------
# Password gate — simple and reliable
# ---------------------------------------------------------------------------

@st.cache_resource
def init_supabase() -> Client:
    """Initialize Supabase client (cached so we don't reconnect on every rerun)."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        st.error("Server configuration error: Supabase credentials are not set.")
        st.stop()
    return create_client(url, key)


def check_login() -> bool:
    """Returns True if user is logged in. Otherwise shows login UI and returns False."""
    supabase = init_supabase()

    # Already logged in this session
    if st.session_state.get("supabase_user"):
        return True

    # Show login UI
    logo_html = f'<img src="{LOGO_SRC}" alt="Pro Talent">' if LOGO_SRC else ""
    st.markdown(
        f"""
        <div class="pt-login-wrap">
            {logo_html}
            <h1>Pro Talent CV Formatter</h1>
            <p>Sign in with your work email</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@protalent.co.za")
            password = st.text_input("Password", type="password", placeholder="Your password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                try:
                    response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": password,
                    })
                    if response.user:
                        st.session_state["supabase_user"] = {
                            "email": response.user.email,
                            "id": response.user.id,
                        }
                        st.rerun()
                    else:
                        st.error("Login failed. Please check your email and password.")
                except Exception:
                    st.error("Incorrect email or password.")
        st.caption(
            "For Pro Talent / Pro Appointments use only. "
            "Contact your team lead if you need a password reset."
        )
    return False
if not check_login():
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
# Branded header — simple, no fragile layouts
# ---------------------------------------------------------------------------

if LOGO_SRC:
    st.markdown(
        f"""
        <div class="pt-header-row">
            <img src="{LOGO_SRC}" alt="Pro Talent">
            <div>
                <p class="pt-header-name">Pro Talent</p>
                <p class="pt-header-tagline">Candidate profile generator</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown("### Pro Talent — Candidate profile generator")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    # Theme toggle
    current_theme = st.session_state.get("app_theme", "light")
    theme_label = "🌙 Dark mode" if current_theme == "light" else "☀️ Light mode"
    if st.button(theme_label, use_container_width=True):
        st.session_state["app_theme"] = "dark" if current_theme == "light" else "light"
        st.rerun()

    st.divider()

with st.sidebar:
    st.subheader("Quick tips")
    st.caption("• Up to 20 CVs per batch")
    st.caption("• PDF and DOCX supported")
    st.caption("• Always review before sending")

    st.divider()

    if st.button("Sign out", use_container_width=True):
        try:
            init_supabase().auth.sign_out()
        except Exception:
            pass
        st.session_state.pop("supabase_user", None)
        st.rerun()


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

st.markdown("### Process candidate CVs")
st.caption(
    "Upload PDFs or Word documents — we'll fill the Pro Talent template "
    "and have profiles ready in seconds."
)

uploaded_cvs = st.file_uploader(
    "Drop CVs here",
    type=["pdf", "docx"],
    accept_multiple_files=True,
    help="PDF or DOCX, up to 20 files at a time.",
)

process_clicked = st.button(
    "Process all CVs",
    type="primary",
    disabled=not uploaded_cvs,
)

if not uploaded_cvs:
    st.caption("Upload some CVs to get started — each one takes about 5–10 seconds.")


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

def resolve_template_path() -> Path:
    return DEFAULT_TEMPLATE


# ---------------------------------------------------------------------------
# Processing — runs only when the user clicks Process all CVs
# Results are saved to session state so they survive reruns from download clicks
# ---------------------------------------------------------------------------

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
            results.append((cv_file.name, str(output_path), data, None))

        except Exception as e:
            results.append((cv_file.name, None, None, f"{type(e).__name__}: {e}"))
            print(traceback.format_exc())

    progress.progress(1.0, text="Done")

    # Save to session state — survives reruns triggered by download clicks
    st.session_state["processing_results"] = results


# ---------------------------------------------------------------------------
# Display results — reads from session state so persists across reruns
# ---------------------------------------------------------------------------

stored_results = st.session_state.get("processing_results", [])

if stored_results:
    st.divider()

    successes = [r for r in stored_results if r[3] is None]
    failures = [r for r in stored_results if r[3] is not None]

    if successes:
        st.success(f"Successfully processed {len(successes)} of {len(stored_results)} CVs")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for _, output_path, _, _ in successes:
                zf.write(output_path, arcname=Path(output_path).name)

        st.download_button(
            label=f"Download all {len(successes)} profiles (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="candidate_profiles.zip",
            mime="application/zip",
            type="primary",
        )

        for cv_name, output_path, data, _ in successes:
            full_name = f"{data.get('first_name', '')} {data.get('surname', '')}".strip()
            with st.expander(f"{full_name or cv_name}"):
                cols = st.columns([2, 1])
                with cols[0]:
                    st.markdown(f"**Name:** {full_name}")
                    st.markdown(f"**Residential area:** {data.get('residential_area', '—')}")
                    st.markdown(f"**Language:** {data.get('language', '—')}")
                    st.markdown(f"**Driver's licence:** {data.get('drivers_licence', '—')}")
                    st.markdown(f"**Current salary:** {data.get('current_salary', '—')}")
                    st.markdown(f"**Required salary:** {data.get('required_salary', '—')}")
                    st.markdown(f"**Availability:** {data.get('availability', '—')}")

                    jobs = data.get("employment_history", [])
                    if isinstance(jobs, list) and jobs:
                        most_recent = jobs[0]
                        if isinstance(most_recent, dict):
                            st.markdown(
                                f"**Most recent role:** {most_recent.get('position', '—')} "
                                f"at {most_recent.get('company', '—')} "
                                f"({most_recent.get('period', '—')})"
                            )

                    fields_to_confirm = []
                    for field in ("identity_number", "equity", "transport", "current_salary", "required_salary"):
                        if "(info absent on CV)" in str(data.get(field, "")):
                            fields_to_confirm.append(field.replace("_", " ").title())
                    if fields_to_confirm:
                        st.warning(
                            "Fields to confirm with candidate during interview: "
                            + ", ".join(fields_to_confirm)
                        )

                with cols[1]:
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="Download this profile",
                            data=f.read(),
                            file_name=Path(output_path).name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_{Path(output_path).name}",
                        )

        # Clear results button — for when user wants to start a fresh batch
        if st.button("Clear results"):
            st.session_state.pop("processing_results", None)
            st.rerun()

    if failures:
        st.error(f"{len(failures)} CV(s) failed to process")
        for cv_name, _, _, error in failures:
            with st.expander(f"Failed: {cv_name}"):
                st.code(error)

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
