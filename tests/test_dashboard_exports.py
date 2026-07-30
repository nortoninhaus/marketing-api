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
    assert 'querySelector(\'[data-testid="stMainBlockContainer"]\')' in SOURCE
    assert '[data-testid="stPopoverButton"]' in SOURCE
    assert "closest('[data-testid=\"stPopover\"]')" in SOURCE
    assert '[data-testid="stPopoverBody"]' in SOURCE
    assert 'popoverBody.style.visibility = "hidden";' in SOURCE
    assert "popoverBody.style.visibility = popoverVisibility;" in SOURCE
    assert "trigger?.click();" not in SOURCE
    assert "onclone: (clonedDoc)" in SOURCE
    assert 'fontFamily.includes("Material Symbols")' in SOURCE
    assert 'a[href^="#"]' in SOURCE
    assert '[data-testid^="stElementToolbar"]' in SOURCE
    assert '[data-testid="stTooltipHoverTarget"]' in SOURCE
    assert '[data-testid="stBaseButton-elementToolbar"]' in SOURCE
    assert '[data-testid="stVegaLiteChart"] details' in SOURCE
    assert 'textContent.includes("Aplicar filtros")' not in SOURCE
    assert 'img[src^="http"]' not in SOURCE
    assert 'querySelectorAll("iframe")' not in SOURCE
    assert 'querySelectorAll("button")' not in SOURCE
    assert "width: target.scrollWidth" in SOURCE
    assert "height: target.scrollHeight" in SOURCE
    assert 'avoid: [".kpi"' not in SOURCE
    assert "Descargar CSV" in SOURCE
    assert 'csv_export_frame["frame"].to_csv(index=False).encode("utf-8-sig")' in SOURCE
    assert 'on_click="ignore"' in SOURCE


def test_meta_campaign_csv_uses_the_displayed_table_data():
    total_append = "pd.concat([campaign_summary, pd.DataFrame([total_row])], ignore_index=True)"
    export_assignment = 'csv_export_frame["frame"] = campaign_summary'

    assert 'csv_export_frame = {"frame": df_curr}' in SOURCE
    assert "data=lambda:" in SOURCE
    assert export_assignment in SOURCE
    assert SOURCE.index(total_append) < SOURCE.index(export_assignment)
