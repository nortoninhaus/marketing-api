# Add automatic PDF and CSV downloads to the dashboard

Add one download control above the rendered report. It opens two actions: an automatic PDF download of the visible report and a CSV download of the current filtered data.

## Decision

Use Streamlit's native `st.popover` and `st.download_button` for the interaction and CSV. Generate the PDF in the browser with a pinned `html2pdf.js` bundle because browser-native printing cannot download automatically and a server-side browser would add unnecessary deployment and session complexity.

## Interaction

1. Show **Descargar** only after a query returns data.
2. Place it before the existing dashboard header.
3. Open a popover containing **Descargar PDF** and **Descargar CSV**.
4. Start each download from its child action without rerunning the dashboard.

## Data flow

### PDF

- Capture the complete main report: header, filters shown in the report, KPIs, charts, cards, and tables.
- Exclude Streamlit chrome, the collapsed sidebar, and the download control itself.
- Save automatically as an A4 landscape, multi-page PDF.
- Build the filename from the platform and selected date range.

### CSV

- Export `df_curr` after the dashboard's applied filters.
- Keep raw column names and values so the file remains useful for analysis.
- Encode as UTF-8 with BOM for spreadsheet compatibility.
- Build the filename from the platform and selected date range.

The previous comparison period is not included because it is not part of the report's detail dataset.

## Failure handling

- Disable or omit the control when no current-period data exists.
- Show a visible error inside the PDF control if the browser library cannot load or capture the report.
- Keep the dashboard state and cached API data unchanged during either download.

Browser security can omit a cross-origin image or iframe whose origin blocks canvas capture. If that occurs in production, the upgrade path is a server-side Chromium export; it is intentionally out of scope until there is evidence it is needed.

## Verification

- Add one focused dashboard UI check covering the top-level popover, both child actions, automatic PDF save call, filtered CSV source, and no-rerun download behavior.
- Run the focused dashboard test and the full dashboard UI test file.
- In a real browser, query a report and verify both files download, the PDF spans the full report, and the CSV opens with accents intact.

## Out of scope

- Server-side PDF storage or email delivery.
- Scheduled exports.
- Custom PDF templates that differ from the rendered dashboard.
