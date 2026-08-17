import ast
import json
from pathlib import Path

import pandas as pd


SOURCE = Path(__file__).resolve().parents[1].joinpath("dashboard.py").read_text()


def test_dashboard_offers_segmented_pdf_and_csv_downloads():
    assert "download_slot = st.empty()" in SOURCE
    assert SOURCE.index("download_slot = st.empty()") < SOURCE.index('<div class="custom-header">')
    export_block = SOURCE[SOURCE.index('with download_slot.container():'):]

    assert 'with st.popover("Descargar", icon=":material/download:", width="content")' in export_block
    assert "segmented_pdf_download_html(export_name, chart_bg)" in export_block
    assert "unsafe_allow_javascript=True" in export_block
    assert "Descargar CSV" in export_block
    assert 'csv_export_frame["frame"].to_csv(index=False).encode("utf-8-sig")' in SOURCE
    assert 'on_click="ignore"' in SOURCE
    assert 'icon=":material/download:"' in export_block
    assert 'width="stretch"' in export_block
    assert "use_container_width" not in export_block
    assert '[data-testid="stPopoverBody"] {' in SOURCE
    assert '[data-testid="stPopoverBody"] > div {' in SOURCE
    assert '[data-testid="stPopoverButton"] *' in SOURCE
    assert '[data-testid="stDownloadButton"] button *' in SOURCE


def test_pdf_capture_uses_page_sized_canvases():
    pdf_source = SOURCE[
        SOURCE.index("def segmented_pdf_download_html"):SOURCE.index("# Determine sidebar collapse state")
    ]

    assert "html2canvas/1.4.1/html2canvas.min.js" in pdf_source
    assert "jspdf/2.5.1/jspdf.umd.min.js" in pdf_source
    assert "for (let pageIndex = 0; pageIndex < pageCount; pageIndex += 1)" in pdf_source
    assert "height: sliceHeight" in pdf_source
    assert "y: pageTop" in pdf_source
    assert "pdf.addPage()" in pdf_source
    assert "canvasHasContent(canvas)" in pdf_source
    assert 'throw new Error("Dashboard capture is empty")' in pdf_source
    assert "renderedPageCount}} páginas" in pdf_source
    assert "height: target.scrollHeight" not in pdf_source


def test_meta_campaign_csv_uses_the_displayed_table_data():
    total_append = "pd.concat([campaign_summary, pd.DataFrame([total_row])], ignore_index=True)"
    export_assignment = 'csv_export_frame["frame"] = campaign_summary'

    assert 'csv_export_frame = {"frame": df_curr}' in SOURCE
    assert "data=lambda:" in SOURCE
    assert export_assignment in SOURCE
    assert SOURCE.index(total_append) < SOURCE.index(export_assignment)
    assert '"budget_display": "Presupuesto"' in SOURCE
    assert '"spend": "Importe gastado"' in SOURCE


def test_csv_download_button_is_executable_code():
    tree = ast.parse(SOURCE)

    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "download_button"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "Descargar CSV"
        for node in ast.walk(tree)
    )


def test_non_meta_table_csv_uses_processed_table_data():
    assignment = 'if platform_key != "meta_ads":\n    csv_export_frame["frame"] = df_table'
    assert assignment in SOURCE
    assert SOURCE.index(assignment) < SOURCE.index('st.dataframe(df_table, width="stretch", hide_index=True)')


def test_html_template_download_is_lazy_and_uses_current_export_frame():
    export_block = SOURCE[SOURCE.index('with download_slot.container():'):]

    assert 'st.selectbox("Template HTML", list(REPORT_TEMPLATES.keys()))' in export_block
    assert 'data=lambda: template_report_html(' in export_block
    assert 'mime="text/html;charset=utf-8"' in export_block
    assert '"Plataformas": selected_platform_label' in export_block
    assert '"Cuenta": account_disp' in export_block
    assert '"Fechas":' in export_block
    assert SOURCE.index('csv_export_frame["frame"] = df_table') < SOURCE.index('with download_slot.container():')


def test_template_report_is_standalone_escaped_and_contains_all_data():
    from dashboard.reporting import build_report_payload, render_report
    tree = ast.parse(SOURCE)
    nodes = [
        node for node in tree.body
        if isinstance(node, (ast.Assign, ast.FunctionDef))
        and (
            isinstance(node, ast.FunctionDef) and node.name == "template_report_html"
            or isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "REPORT_TEMPLATES" for target in node.targets)
        )
    ]
    namespace = {
        "pd": pd,
        "html": __import__("html"),
        "build_report_payload": build_report_payload,
        "render_report": render_report,
        "Any": __import__("typing").Any,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "dashboard.py", "exec"), namespace)
    frame = pd.DataFrame({"campaign_name": ["Campaign Alpha", "Campaign Beta"], "spend": [1234.56, 20.0], "impressions": [50000, 1200]})

    assert set(namespace["REPORT_TEMPLATES"]) == {"Nutri", "Adriana Hoyos", "ARTZ", "Shamuna"}

    for template_name in namespace["REPORT_TEMPLATES"]:
        report = namespace["template_report_html"](
            frame,
            template_name,
            {
                "Cuenta": "Cliente & uno",
                "Fechas": "01/08/2026 – 13/08/2026",
                "start_date": "2026-08-01",
                "end_date": "2026-08-13",
                "platform": "meta_ads",
                "Plataformas": "Meta Ads (Facebook/IG)",
            },
        )
        assert report.startswith("<!doctype html>")
        assert "REPORT_DATA" in report
        assert "Cliente \\u0026 uno" in report or "Cliente & uno" in report or "Cliente &amp; uno" in report
        data_json = report.split('<script id="report-data" type="application/json">')[1].split("</script>")[0]
        parsed_data = json.loads(data_json)
        assert parsed_data["summary"]["spend"] == 1254.56
        assert parsed_data["summary"]["impressions"] == 51200
        assert parsed_data["meta"]["period"]["start"] == "2026-08-01"
        assert parsed_data["meta"]["period"]["end"] == "2026-08-13"
        assert bool(parsed_data["by_platform"]) is True

