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
    initial_sidebar_state="auto",
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
</style>
"""

st.markdown(LIGHT_CSS, unsafe_allow_html=True)


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

def check_password() -> bool:
    expected_password = os.getenv("APP_PASSWORD")

    if not expected_password:
        return True  # No password configured — local dev mode

    if st.session_state.get("authenticated"):
        return True

    logo_html = f'<img src="{LOGO_SRC}" alt="Pro Talent">' if LOGO_SRC else ""

    st.markdown(
        f"""
        <div class="pt-login-wrap">
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
            submitted = st.form_submit_button(
                "Sign in", type="primary", use_container_width=True
            )

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
    st.subheader("Template")
    custom_template = st.file_uploader(
        "Upload custom template (.docx)",
        type=["docx"],
        help="Optional. Upload your own .docx template with {{placeholder}} tokens.",
    )
    if custom_template:
        st.success("Custom template loaded")
    else:
        st.caption("Using default Pro Talent template")

    st.divider()

    st.subheader("Quick tips")
    st.caption("• Up to 20 CVs per batch")
    st.caption("• PDF and DOCX supported")
    st.caption("• Always review before sending")

    st.divider()

    if st.button("Sign out", use_container_width=True):
        st.session_state.pop("authenticated", None)
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
    if custom_template:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp.write(custom_template.getvalue())
        tmp.close()
        return Path(tmp.name)
    return DEFAULT_TEMPLATE


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

    # ---- Results ----
    st.divider()

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
