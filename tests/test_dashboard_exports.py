import ast
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1].joinpath("dashboard.py").read_text()


def test_dashboard_offers_compact_csv_download():
    assert "download_slot = st.empty()" in SOURCE
    assert SOURCE.index("download_slot = st.empty()") < SOURCE.index('<div class="custom-header">')
    export_block = SOURCE[SOURCE.index('with download_slot.container():'):SOURCE.index("# HERO RENDER")]

    assert 'with st.popover("Descargar", icon=":material/download:", width="content")' in export_block
    assert "Descargar PDF" not in export_block
    assert "html2pdf.bundle.min.js" not in export_block
    assert "components.html" not in export_block
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
