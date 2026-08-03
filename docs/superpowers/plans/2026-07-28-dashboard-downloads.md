# Dashboard PDF and CSV Downloads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one top-level dashboard control that automatically downloads the rendered report as PDF or its current filtered data as CSV.

**Architecture:** Reserve a Streamlit placeholder before the existing header and populate it after `df_curr` has been fetched and filtered. Use native Streamlit controls for the popover and CSV; use a sandbox-compatible `components.html` button with pinned `html2pdf.js` for the browser-side PDF capture.

**Tech Stack:** Python 3, Streamlit 1.58, pandas, JavaScript, html2pdf.js 0.10.1, pytest.

## Global Constraints

- The PDF download must be automatic; do not use the browser print dialog.
- One **Descargar** control must reveal exactly **Descargar PDF** and **Descargar CSV**.
- Export only after current-period data exists.
- Capture the main report in A4 landscape pages; exclude Streamlit chrome, the sidebar, and the export control.
- Export filtered `df_curr` as UTF-8 with BOM and do not include the comparison-period frame.
- Do not add a Python dependency or modify `requirements.txt`.
- Preserve the existing uncommitted theme changes in `dashboard.py` and `tests/test_dashboard_ui.py`.
- Do not modify `tests/test_dashboard_ui.py`; its baseline is currently four known failures and five passes.

---

### Task 1: Add the grouped automatic exports

**Files:**
- Create: `tests/test_dashboard_exports.py`
- Modify: `dashboard.py:913-925`
- Modify: `dashboard.py:1157-1160`

**Interfaces:**
- Consumes: filtered `df_curr: pandas.DataFrame`, `selected_platform_label: str`, `start_date: date`, `end_date: date`, and `chart_bg: str`.
- Produces: a top-positioned `st.popover` with one automatic `.pdf` download and one automatic `.csv` download.
- External browser asset: `https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js`.

- [ ] **Step 1: Write the failing export UI check**

Create `tests/test_dashboard_exports.py`:

```python
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1].joinpath("dashboard.py").read_text()


def test_dashboard_offers_grouped_automatic_pdf_and_csv_downloads():
    assert "download_slot = st.empty()" in SOURCE
    assert SOURCE.index("download_slot = st.empty()") < SOURCE.index('<div class="custom-header">')
    assert 'with st.popover("Descargar"' in SOURCE
    assert "Descargar PDF" in SOURCE
    assert "html2pdf.bundle.min.js" in SOURCE
    assert ".from(target).save()" in SOURCE
    assert "data-export-control" in SOURCE
    assert "Descargar CSV" in SOURCE
    assert 'df_curr.to_csv(index=False).encode("utf-8-sig")' in SOURCE
    assert 'on_click="ignore"' in SOURCE
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_dashboard_exports.py::test_dashboard_offers_grouped_automatic_pdf_and_csv_downloads -q
```

Expected: FAIL at `assert "download_slot = st.empty()" in SOURCE` because no export control exists yet.

- [ ] **Step 3: Reserve the top position**

In `dashboard.py`, immediately after `# MAIN DISPLAY (Occupies full wide screen)` and before `# Header`, add:

```python
download_slot = st.empty()
```

- [ ] **Step 4: Populate the menu after filters are applied**

In `dashboard.py`, immediately before `# HERO RENDER (Clean, full width, no Sipy logo)`, add:

```python
export_slug = re.sub(r"[^a-z0-9]+", "-", selected_platform_label.lower()).strip("-")
export_name = f"{export_slug}_{start_date:%Y-%m-%d}_{end_date:%Y-%m-%d}"

with download_slot.container():
    with st.popover("Descargar", icon=":material/download:"):
        components.html(f"""
        <style>
        body {{ margin: 0; font-family: Manrope, Arial, sans-serif; }}
        button {{
            width: 100%;
            padding: 0.55rem 0.75rem;
            border: 1px solid #1AE08C;
            border-radius: 0.5rem;
            background: #1AE08C;
            color: #0A0D13;
            font-weight: 700;
            cursor: pointer;
        }}
        button:disabled {{ cursor: wait; opacity: 0.65; }}
        #pdf-status {{ min-height: 1rem; margin: 0.3rem 0 0; color: #FF4B4B; font-size: 0.75rem; }}
        </style>
        <button id="pdf-download" type="button">Descargar PDF</button>
        <p id="pdf-status" role="status" aria-live="polite"></p>
        <script>
        const parentDoc = window.parent.document;
        const button = document.getElementById("pdf-download");
        const status = document.getElementById("pdf-status");
        const trigger = Array.from(parentDoc.querySelectorAll("button")).find(
            (candidate) => candidate.textContent.trim() === "Descargar"
        );
        const exportControl = trigger?.closest('[data-testid="stElementContainer"], .element-container');
        if (exportControl) exportControl.dataset.exportControl = "true";

        const loadHtml2Pdf = () => {{
            if (window.html2pdf) return Promise.resolve(window.html2pdf);
            return new Promise((resolve, reject) => {{
                const script = document.createElement("script");
                script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
                script.onload = () => resolve(window.html2pdf);
                script.onerror = () => reject(new Error("html2pdf failed to load"));
                document.head.appendChild(script);
            }});
        }};

        button.addEventListener("click", async () => {{
            button.disabled = true;
            status.textContent = "Generando PDF…";
            try {{
                const html2pdf = await loadHtml2Pdf();
                const target = parentDoc.querySelector('[data-testid="stMainBlockContainer"]');
                if (!target) throw new Error("Dashboard report container not found");

                // ponytail: browser capture avoids a server-side Chromium service; upgrade if cross-origin embeds must be exact.
                await html2pdf().set({{
                    margin: [8, 8, 8, 8],
                    filename: "{export_name}.pdf",
                    image: {{ type: "jpeg", quality: 0.95 }},
                    html2canvas: {{
                        scale: 1.5,
                        useCORS: true,
                        backgroundColor: "{chart_bg}",
                        windowWidth: target.scrollWidth,
                        windowHeight: target.scrollHeight,
                        ignoreElements: (element) => Boolean(
                            element.closest?.('[data-export-control="true"]')
                        ),
                    }},
                    jsPDF: {{ unit: "mm", format: "a4", orientation: "landscape" }},
                    pagebreak: {{
                        mode: ["css", "legacy"],
                        avoid: [".kpi", ".hero-card", "[data-testid='stVegaLiteChart']"],
                    }},
                }}).from(target).save();
                status.textContent = "";
            }} catch (error) {{
                console.error("PDF export failed", error);
                status.textContent = "No se pudo generar el PDF.";
            }} finally {{
                button.disabled = false;
            }}
        }});
        </script>
        """, height=72)
        st.download_button(
            "Descargar CSV",
            data=df_curr.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{export_name}.csv",
            mime="text/csv;charset=utf-8",
            on_click="ignore",
            use_container_width=True,
        )
```

- [ ] **Step 5: Run the focused test and verify GREEN**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_dashboard_exports.py -q
```

Expected: `1 passed`.

- [ ] **Step 6: Verify Python syntax and patch cleanliness**

Run:

```bash
.venv/bin/python -m py_compile dashboard.py tests/test_dashboard_exports.py
git diff --check
```

Expected: both commands exit 0 with no output.

- [ ] **Step 7: Check the existing dashboard UI baseline**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_dashboard_ui.py -q
```

Expected baseline until the unrelated local work is reconciled: four existing failures and five passes. The four failure names must remain:

```text
test_dashboard_has_light_dark_and_spanish_meta_labels
test_dashboard_hashtag_ranking_uses_returned_post_text
test_regions_are_localized_and_charted
test_campaign_names_are_cleaned_for_display
```

Stop if the export change introduces any additional failure.

- [ ] **Step 8: Exercise both downloads in the real dashboard**

Run outside the sandbox if socket binding requires approval:

```bash
PYTHONPATH=. .venv/bin/streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501
```

In an authenticated development session:

1. Query any account with non-empty current-period data.
2. Confirm **Descargar** appears before the report header and reveals exactly two actions.
3. Click **Descargar PDF** and verify a multi-page landscape PDF downloads without a print dialog.
4. Click **Descargar CSV** and verify the CSV downloads without a rerun and opens with accents intact.

If no development login or API-backed report is available, record this runtime step as N/A because the export control is behind authenticated, non-empty query state; do not claim end-to-end browser verification.

- [ ] **Step 9: Commit only the export work unit**

The target file already contains unrelated uncommitted changes. Stage only the new export hunks:

```bash
git add tests/test_dashboard_exports.py
git add -p dashboard.py
git diff --cached --check
git diff --cached --stat
git commit -m "feat: add dashboard PDF and CSV downloads"
```

Expected staged scope: `tests/test_dashboard_exports.py` plus the two export-only hunks in `dashboard.py`. Do not stage `tests/test_dashboard_ui.py` or the pre-existing theme hunks.

Rollback boundary: revert this feature commit to remove the export placeholder, popover, browser PDF capture, CSV download, and focused export test without touching the existing theme work.
