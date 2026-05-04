"""
app.py
------
Streamlit web app — the recruiter-facing UI.

Deployment-ready version:
- Password protected (set APP_PASSWORD env var)
- API key read from environment (set ANTHROPIC_API_KEY env var)
- Uses session state to remember login during the session

Run locally:
    streamlit run app.py
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

DEFAULT_TEMPLATE = Path(__file__).parent / "templates" / "pro_talent_template.docx"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Page config — runs first
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="CV → Pro Talent Template",
    page_icon="📄",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Password gate
# ---------------------------------------------------------------------------

def check_password() -> bool:
    """Show password screen until correct password entered. Returns True if logged in."""

    expected_password = os.getenv("APP_PASSWORD")

    # If no password is configured, skip gate (useful for local development)
    if not expected_password:
        return True

    # Already logged in?
    if st.session_state.get("authenticated"):
        return True

    # Show login screen
    st.title("🔒 Pro Talent CV Formatter")
    st.caption("Enter the team password to continue")

    with st.form("login_form"):
        entered = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", type="primary")

        if submitted:
            if entered == expected_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")

    st.info(
        "This app is for Pro Talent / Pro Appointments use only. "
        "If you don't have the password, contact your team lead."
    )
    return False


if not check_password():
    st.stop()


# ---------------------------------------------------------------------------
# API key — must be set as environment variable on Railway
# ---------------------------------------------------------------------------

api_key = os.getenv("ANTHROPIC_API_KEY")

if not api_key:
    st.error(
        "⚠️ Server configuration error: ANTHROPIC_API_KEY is not set. "
        "If you're an admin, set this environment variable in your hosting platform."
    )
    st.stop()


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------

st.title("📄 CV → Pro Talent Template")
st.caption(
    "Upload candidate CVs and get back filled Pro Talent profiles ready to send to clients. "
    "Powered by Claude AI."
)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Options")

    custom_template = st.file_uploader(
        "Custom template (optional)",
        type=["docx"],
        help=(
            "Upload your own template if you want to override the default Pro Talent one. "
            "Use {{placeholder}} tokens in the right places."
        ),
    )

    if custom_template:
        st.success("Custom template loaded")
    else:
        st.info("Using Pro Talent template")

    st.divider()

    st.markdown(
        "**Tips**\n"
        "- Process up to 20 CVs at once\n"
        "- PDF and DOCX supported\n"
        "- Always review before sending to clients"
    )

    st.divider()

    if st.button("Sign out", use_container_width=True):
        st.session_state.pop("authenticated", None)
        st.rerun()


# ---------------------------------------------------------------------------
# Upload area
# ---------------------------------------------------------------------------

uploaded_cvs = st.file_uploader(
    "Upload CVs",
    type=["pdf", "docx"],
    accept_multiple_files=True,
    help="Drop one or more CVs here. PDF and Word files supported.",
)

col1, col2 = st.columns([1, 4])
with col1:
    process_clicked = st.button(
        "🚀 Process CVs",
        type="primary",
        disabled=not uploaded_cvs,
        use_container_width=True,
    )
with col2:
    if not uploaded_cvs:
        st.info("Upload some CVs to get started.")


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

    progress.progress(1.0, text="Done!")

    # ---- Show results ----
    st.divider()
    st.subheader("📋 Results")

    successes = [r for r in results if r[3] is None]
    failures = [r for r in results if r[3] is not None]

    if successes:
        st.success(f"✅ Successfully processed {len(successes)} of {len(results)} CVs")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for _, output_path, _, _ in successes:
                zf.write(output_path, arcname=output_path.name)

        st.download_button(
            label=f"📥 Download all {len(successes)} filled templates (ZIP)",
            data=zip_buffer.getvalue(),
            file_name="candidate_profiles.zip",
            mime="application/zip",
            type="primary",
        )

        for cv_name, output_path, data, _ in successes:
            full_name = f"{data.get('first_name', '')} {data.get('surname', '')}".strip()
            with st.expander(f"✅ {full_name or cv_name}  —  from {cv_name}"):
                cols = st.columns([2, 1])
                with cols[0]:
                    st.markdown(f"**Name:** {full_name}")
                    st.markdown(f"**Residential Area:** {data.get('residential_area', '—')}")
                    st.markdown(f"**Language:** {data.get('language', '—')}")
                    st.markdown(f"**Driver's Licence:** {data.get('drivers_licence', '—')}")
                    st.markdown(f"**Current Salary:** {data.get('current_salary', '—')}")
                    st.markdown(f"**Required Salary:** {data.get('required_salary', '—')}")
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
                            "⚠️ Not in CV — please ask candidate during interview: "
                            + ", ".join(fields_to_confirm)
                        )

                with cols[1]:
                    with open(output_path, "rb") as f:
                        st.download_button(
                            label="📥 Download this profile",
                            data=f.read(),
                            file_name=output_path.name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_{output_path.name}",
                        )
                    with st.popover("View full extraction"):
                        st.json(data)

    if failures:
        st.error(f"❌ {len(failures)} CV(s) failed to process")
        for cv_name, _, _, error in failures:
            with st.expander(f"❌ {cv_name}"):
                st.code(error)


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.divider()
with st.expander("ℹ️ How it works"):
    st.markdown("""
    **Pipeline:**
    1. **Text extraction** — pulls raw text from PDF or Word CVs
    2. **AI structuring** — Claude reads the CV and returns structured data
    3. **Template filling** — populates the Pro Talent template

    **Important:** Always review filled profiles before sending to clients.
    Replace any "(info absent on CV)" markers with real info from your interview.
    """)
