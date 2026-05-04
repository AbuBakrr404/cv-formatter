# CV → Pro Talent Master Template Automation

Drop CVs in, get filled Pro Talent candidate profiles out, ready to send to clients.

## What it does

```
   CVs (PDF/DOCX)        Claude reads them          Pro Talent template
   ──────────────  ──→   like a recruiter   ──→     filled and ready
                         would
```

For each CV:
1. **Extracts text** from PDF or Word
2. **Sends to Claude** which returns clean structured data (name, contact, work history, education, skills, etc.)
3. **Fills your Pro Talent master template** — keeping logo, blue headers, footer, and layout exactly as-is

## Fields automatically extracted from CVs

| Pro Talent field | What gets filled in |
|---|---|
| Surname / First Name | From the CV |
| Residential Area | From the CV |
| Language | From the CV |
| Driver's Licence | If mentioned |
| Achievements & Certifications | All achievements from the CV |
| Computer Literacy & Skills | All technical skills mentioned |
| Education (2 slots) | Most recent 2 qualifications |
| Employment History (3 slots) | Most recent 3 roles, with full duties |

## Fields the recruiter fills in after the interview

These don't appear on most CVs, so the system marks them clearly so nothing is missed:

| Field | Default value |
|---|---|
| Identity Number | `(info absent on CV)` |
| Equity | `(info absent on CV)` |
| Transport | `(info absent on CV)` (unless CV says "own car") |
| Current Salary | `(info absent on CV)` (unless on CV) |
| Required Salary | `(info absent on CV)` (unless on CV) |
| Availability | `(info absent on CV)` (unless on CV) |
| ITC / Criminal Record | `None` (recruiter updates if disclosed) |
| Reason for Leaving (each role) | `(info absent on CV)` |
| Reference 1 / 2 | Left as `To Follow` |

## Quick start

### First-time setup (one-off, ~20 minutes)

1. **Install Python** from [python.org/downloads](https://python.org/downloads) — tick "Add python.exe to PATH" during install
2. **Unzip** this folder to your Desktop
3. **Open a terminal** in this folder (in Windows: click the address bar in File Explorer, type `cmd`, press Enter)
4. **Install dependencies:** `pip install -r requirements.txt`
5. **Get an Anthropic API key** at [console.anthropic.com](https://console.anthropic.com) and add at least $5 of credit (covers ~200-500 CVs)

### Daily use

1. Open the `cv_automation` folder
2. Open terminal (address bar → `cmd` → Enter)
3. Run: `streamlit run app.py`
4. Drop CVs into the web page, click "Process CVs", download the filled templates
5. **Review each profile** — fix anything Claude got wrong, fill in the `(info absent on CV)` items after your interview, then send to client

### Try it without an API key first

`python test_pipeline.py`

This uses a fake candidate (Sipho Mthembu) so you can see exactly what a filled output looks like without spending any API credit.

## Files in this project

```
cv_automation/
├── app.py                                  # Streamlit web UI - recruiters use this
├── cv_parser.py                            # Reads PDF/DOCX text
├── ai_extractor.py                         # Sends CVs to Claude
├── template_filler.py                      # Fills the Pro Talent template
├── inject_pro_talent_placeholders.py       # Re-runs placeholder injection (dev tool)
├── test_pipeline.py                        # Test without using API
├── requirements.txt
├── .env.example
├── templates/
│   └── pro_talent_template.docx            # Your master template with placeholders
├── sample_data/
│   └── sample_cv.docx                      # Sample CV for testing
└── output/                                 # Filled templates appear here
```

## Tips for daily use

- **Always review before sending.** Claude is very accurate but not perfect. Watch out for: salary figures buried in narrative text, unusual name spellings, dates in obscure formats.
- **The `(info absent on CV)` markers are a checklist.** Fill them in after your interview, then the profile is client-ready.
- **Fewer than 3 jobs?** The extra slots will appear blank. Delete them in Word before sending, or leave them.
- **More than 3 jobs?** Only the 3 most recent are populated. If you need older roles, edit the .docx manually after.
- **CV is a scanned image?** The system reads text-based PDFs. For scanned ones, OCR first using a free service like ilovepdf.com/ocr-pdf.
- **Cost:** Roughly R0.20-R0.50 per CV. A team doing 15 CVs/day spends ~R200/month in API costs.

## Customizing the template

If you want to change the master template (different colours, new sections, reordered fields):

1. Open `templates/pro_talent_template.docx` in Word
2. Edit anything visible — logo, colours, section headings, layout
3. Don't change the `{{placeholder}}` tokens unless you also update `template_filler.py`
4. Save (keep `.docx` format)

If you want to add a NEW field (e.g. "Notice Period in Weeks"):

1. Add to `EXTRACTION_SCHEMA` in `ai_extractor.py`:
   `"notice_weeks": "Notice period in weeks if specified",`

2. Add to `template_filler.py` in the `simple_replacements` dict:
   `"{{notice_weeks}}": _safe_str(candidate_data.get("notice_weeks")),`

3. Use `{{notice_weeks}}` anywhere in your Word template

## Troubleshooting

| Problem | Fix |
|---|---|
| `python is not recognized` | Reinstall Python with "Add to PATH" ticked |
| `pip is not recognized` | Same as above |
| `streamlit is not recognized` | Re-run `pip install -r requirements.txt` |
| Authentication error in app | Check API key has no extra spaces; check billing at console.anthropic.com |
| Education/jobs blank in output | CV with very unusual layout — try re-saving as fresh DOCX |
| Some fields show `(info absent on CV)` | Intentional — they're not in the CV. Fill in after interview. |
| Empty job slots in output | Candidate has fewer than 3 jobs — delete extra blocks in Word |

## Privacy & data handling

CV text is sent to Anthropic's API to be processed by Claude. Anthropic does NOT train on data sent through the API. Pro Talent's data handling policies should be reviewed before processing CVs of candidates who have not consented to AI-assisted processing.

## Built with

Anthropic Claude API · Streamlit · python-docx · pdfplumber
