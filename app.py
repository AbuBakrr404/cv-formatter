"""
app.py
------
Streamlit web app — the recruiter-facing UI.

Pro Talent branded version:
- Pro Talent red primary colour
- Logo and brand header at the top
- Branded login screen
- Sentence case throughout, no emoji-heavy default Streamlit copy

Deployment-ready:
- Password protected (set APP_PASSWORD env var)
- API key read from environment (set ANTHROPIC_API_KEY env var)
"""

import io
import os
import zipfile
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
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent
DEFAULT_TEMPLATE = PROJECT_ROOT / "templates" / "pro_talent_template.docx"
LOGO_PATH = PROJECT_ROOT / "assets" / "pro_talent_logo.png"
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Page config — runs first
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Pro Talent · CV Formatter",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Custom CSS injection — small touches that make Streamlit feel branded
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
    /* Pro Talent red accent bar across top of main content */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
    }

    /* Tighten spacing in branded header */
    .pt-header {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 12px 18px 14px 18px;
        background: white;
        border: 1px solid #E5E7EB;
        border-bottom: 3px solid #C8102E;
        border-radius: 10px 10px 0 0;
        margin-bottom: 0;
    }
    .pt-header img {
        width: 44px;
        height: 44px;
        border-radius: 8px;
        flex-shrink: 0;
    }
    .pt-header .pt-text {
        flex: 1;
    }
    .pt-header .pt-name {
        font-size: 16px;
        font-weight: 600;
        color: #1F2937;
        line-height: 1.2;
        margin: 0;
    }
    .pt-header .pt-tagline {
        font-size: 12px;
        color: #6B7280;
        margin: 2px 0 0;
    }

    /* Info banner just below the header */
    .pt-info-banner {
        background: #EFF6FF;
        border: 1px solid #DBEAFE;
        border-top: 0;
        padding: 8px 18px;
        font-size: 12px;
        color: #1E40AF;
        border-radius: 0 0 10px 10px;
        margin-bottom: 24px;
    }

    /* Section labels (small uppercase headings) */
    .pt-label {
        font-size: 11px;
        font-weight: 600;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0 0 8px 0;
    }

    /* Footer (small, muted) */
    .pt-footer {
        text-align: center;
        font-size: 11px;
        color: #9CA3AF;
        margin-top: 32px;
        padding-top: 16px;
        border-top: 1px solid #F3F4F6;
    }

    /* Login screen polish */
    .pt-login-wrapper {
        max-width: 380px;
        margin: 40px auto 0;
        text-align: center;
    }
    .pt-login-wrapper img {
        width: 64px;
        height: 64px;
        border-radius: 12px;
        margin-bottom: 16px;
    }
    .pt-login-wrapper h1 {
        font-size: 22px;
        font-weight: 600;
        color: #1F2937;
        margin: 0 0 4px;
    }
    .pt-login-wrapper p {
        font-size: 13px;
        color: #6B7280;
        margin: 0 0 20px;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Password gate
# ---------------------------------------------------------------------------

def check_password() -> bool:
    """Show password screen until correct password entered. Returns True if logged in."""

    expected_password = os.getenv("APP_PASSWORD")

    # If no password is configured, skip gate (useful for local development)
    if not expected_password:
        return True

    if st.session_state.get("authenticated"):
        return True

    # Branded login screen
    logo_html = ""
    if LOGO_PATH.exists():
        import base64
        with open(LOGO_PATH, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{encoded}" alt="Pro Talent">'

    st.markdown(
        f"""
        <div class="pt-login-wrapper">
            {logo_html}
            <h1>Pro Talent CV Formatter</h1>
            <p>Sign in with your team password to continue</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Centred form using columns
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.form("login_form", clear_on_submit=False):
            entered = st.text_input("Team password", type="password", label_visibility="collapsed", placeholder="Team password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

            if submitted:
                if entered == expected_password:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Please try again.")

        st.caption(
            "For Pro Talent / Pro Appointments use only. "
            "Contact your team lead if you don't have the password."
        )

    return False


if not check_password():
    st.stop()


# ---------------------------------------------------------------------------
# API key — must be set as environment variable
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

if LOGO_PATH.exists():
    import base64
    with open(LOGO_PATH, "rb") as f:
        encoded_logo = base64.b64encode(f.read()).decode("utf-8")
    logo_src = f"data:image/png;base64,{encoded_logo}"
else:
    logo_src = ""

st.markdown(
    f"""
    <div class="pt-header">
        <img src="{logo_src}" alt="Pro Talent">
        <div class="pt-text">
            <p class="pt-name">Pro Talent</p>
            <p class="pt-tagline">Candidate profile generator</p>
        </div>
    </div>
    <div class="pt-info-banner">
        Using <strong>Default Pro Talent</strong> template — upload a custom one in the sidebar if needed
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar — settings & sign out
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown('<p class="pt-label">Template</p>', unsafe_allow_html=True)
    custom_template = st.file_uploader(
        "Upload custom template (.docx)",
        type=["docx"],
        help=(
            "Optional. Upload your own template to override the default Pro Talent one. "
            "Use {{placeholder}} tokens in the right places."
        ),
        label_visibility="collapsed",
    )

    if custom_template:
        st.success("Custom template loaded")
    else:
        st.caption("Using default Pro Talent template")

    st.divider()

    st.markdown('<p class="pt-label">Quick tips</p>', unsafe_allow_html=True)
    st.caption("Up to 20 CVs per batch")
    st.caption("PDF and DOCX supported")
    st.caption("Always review before sending")

    st.divider()

    if st.button("Sign out", use_container_width=True):
        st.session_state.pop("authenticated", None)
        st.rerun()


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

st.markdown("### Process candidate CVs")
st.caption(
    "Upload PDFs or Word documents. We'll fill the Pro Talent template "
    "and have profiles ready in seconds."
)

uploaded_cvs = st.file_uploader(
    "Drop CVs here",
    type=["pdf", "docx"],
    accept_multiple_files=True,
    help="PDF or DOCX. Up to 20 files at a time.",
)

col1, col2 = st.columns([1, 4])
with col1:
    process_clicked = st.button(
        "Process all CVs",
        type="primary",
        disabled=not uploaded_cvs,
        use_container_width=True,
    )
with col2:
    if not uploaded_cvs:
        st.caption("Upload some CVs to get started — each one takes about 5–10 seconds.")


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

def resolve_template_path() -> Path:
    """Return path to template (custom upload or default)."""
    if custom_template:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp.write(custom_template.getvalue())
        tmp.close()
        return Path(tmp.name)
    return DEFAULT_TEMPLATE


if process_clicked:
    template_path = resolve_template_path()

    if not template_path.exists():
        st.error(f"Template not found at {template_path}.")
        st.stop()

    results = []
    progress = st.progress(0, text="Starting…")

    for i, cv_file in enumerate(uploaded_cvs):
        progress.progress(
            i / len(uploaded_cvs),
            text=f"Processing {cv_file.name}… ({i + 1}/{len(uploaded_cvs)})"
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

    # ---- Show results ----
    st.divider()
    st.markdown('<p class="pt-label">Results</p>', unsafe_allow_html=True)

    successes = [r for r in results if r[3] is None]
    failures = [r for r in results if r[3] is not None]

    if successes:
        st.success(f"Successfully processed {len(successes)} of {len(results)} CVs")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for _, output_path, _, _ in successes:
                zf.write(output_path, arcname=output_path.name)

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
                            file_name=output_path.name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_{output_path.name}",
                        )
                    with st.popover("View full extraction"):
                        st.json(data)

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
