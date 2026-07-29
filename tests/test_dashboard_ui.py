import ast
from pathlib import Path
from types import SimpleNamespace

import requests
from streamlit.testing.v1 import AppTest

from dashboard.api import process_api_response
from dashboard.auth import create_dashboard_token

DASHBOARD_PATH = Path(__file__).resolve().parents[1] / "dashboard.py"
SOURCE = DASHBOARD_PATH.read_text()


def test_dashboard_has_light_dark_and_spanish_meta_labels():
    assert 'st.sidebar.button(theme_icon, key="theme_switch_button"' in SOURCE
    assert 'st.sidebar.radio("Tema", ["Claro", "Oscuro"]' not in SOURCE
    assert '"male": "Masculino"' in SOURCE
    assert '"female": "Femenino"' in SOURCE
    assert "Desempeño de campañas destacadas" in SOURCE
    assert "Ranking de hashtags (Instagram)" in SOURCE


def test_theme_change_does_not_refetch_official_meta_data():
    assert "dashboard_query_cache" in SOURCE
    assert "query_key" in SOURCE
    assert 'st.session_state["dashboard_query_cache"][query_key]' in SOURCE
    assert "meta_official_cache" in SOURCE
    assert "official_key" in SOURCE
    assert 'st.session_state["meta_official_cache"][official_key]' in SOURCE


def test_theme_change_preserves_sidebar_state(monkeypatch):
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: SimpleNamespace(status_code=200, json=lambda: []),
    )
    app = AppTest.from_file(DASHBOARD_PATH, default_timeout=20)
    app.session_state["dashboard_auth_token"] = create_dashboard_token(
        {
            "username": "test",
            "client_id": "client_1",
            "user_id": "user_1",
            "accounts": {},
        }
    )

    app.run()
    app.sidebar.multiselect[0].select("Meta Ads (Facebook/IG)").run()
    app.sidebar.button[0].click().run()

    assert not app.exception
    assert app.sidebar.button[0].label == "☀"
    assert app.sidebar.multiselect[0].value == ["Meta Ads (Facebook/IG)"]


def test_theme_change_uses_polygon_gradient_view_transition():
    assert "parentDoc.startViewTransition" in SOURCE
    assert "M0 0H40L0 40V0Z" in SOURCE
    assert "mask-size: 200vmax" in SOURCE
    assert "unsafe_allow_javascript=True" in SOURCE


def test_charts_and_header_follow_selected_theme():
    assert 'chart_bg = "#FFFFFF" if theme_mode == "Claro" else "#0A0D13"' in SOURCE
    assert 'text_color = "#0F172A" if theme_mode == "Claro" else "#EAF0F7"' in SOURCE
    assert ".agency img { filter:" in SOURCE


def test_dashboard_hashtag_ranking_uses_returned_post_text():
    assert "ad_hashtag_rows" in SOURCE
    assert "effective_object_story_id" in SOURCE
    assert '"post_message": post_text' in SOURCE
    assert 'preview.get("body", "")' in SOURCE
    assert 'preview.get("post_message", "")' in SOURCE
    assert 'text_col = "caption" if "caption" in df_curr.columns else "campaign_name"' in SOURCE
    assert 're.findall(r"#[\\wáéíóúÁÉÍÓÚñÑ]+", text)' in SOURCE
    assert "No se encontraron hashtags" in SOURCE


def test_regions_are_localized_and_charted():
    assert "clean_region_name" in SOURCE
    assert 're.sub(r"\\s+Province$"' in SOURCE
    assert 'st.markdown("#### Regiones principales")' in SOURCE
    assert "region_chart" in SOURCE


def test_campaign_names_are_cleaned_for_display():
    assert "clean_campaign_name" in SOURCE
    assert '"campaign_label": clean_campaign_name(campaign_name)' in SOURCE
    assert '"campaign_label": "Campaña"' in SOURCE


def test_sidebar_actions_are_ordered_without_a_separator():
    query_button = 'st.sidebar.button("🚀 Consultar API"'
    logout_button = 'st.sidebar.button("🔒 Cerrar Sesión"'

    assert SOURCE.index(query_button) < SOURCE.index(logout_button)
    assert 'st.sidebar.markdown("---")' not in SOURCE
    assert ".inhaus-logout-container {" not in SOURCE


def test_ads_cards_show_real_leads_and_total_reach():
    df = process_api_response(
        [{
            "campaign_name": "Lead campaign",
            "date": "2026-07-01",
            "metrics": {"conversions": 999, "lead": 7, "reach": 123},
        }],
        "meta_ads",
        "client_1",
        "user_1",
    )

    assert df["lead"].sum() == 7
    assert 'standard_metrics = ["impressions", "clicks", "spend", "conversions", "lead", "reach", "__results__", "cost_per_result"]' in SOURCE
    assert 'curr_primary = df_curr["lead"].sum()' in SOURCE
    assert 'primary_label = "Clientes Potenciales"' in SOURCE
    assert 'get_kpi_card_html("Alcance Total", f"{total_reach_curr:,}"' in SOURCE
    assert '"Costo por Conversión (CPA)"' not in SOURCE


def test_featured_campaigns_show_requested_meta_metrics():
    df = process_api_response(
        [{
            "campaign_name": "Lead campaign",
            "date": "2026-07-01",
            "metrics": {
                "__results__": 7,
                "cost_per_result": 0.42,
                "reach": 100,
                "impressions": 200,
                "clicks": 10,
                "spend": 50,
            },
        }],
        "meta_ads",
        "client_1",
        "user_1",
    )

    assert df["results"].sum() == 7
    assert df["cost_per_result"].sum() == 0.42
    assert '"__results__"' in SOURCE
    for label in (
        "Resultados",
        "Costo por resultado",
        "Reach",
        "CPM",
        "Impressions",
        "Clicks",
        "CPC",
        "Inversión",
    ):
        assert f'"{label}"' in SOURCE
    assert '"cost_per_result": "mean"' in SOURCE
    assert 'ranked_campaigns["cost_per_result"] = ranked_campaigns["spend"].div(ranked_campaigns["results"])' not in SOURCE
    assert 'ranked_campaigns["cpm"] = ranked_campaigns["spend"].mul(1000).div(ranked_campaigns["impressions"])' in SOURCE
    assert 'ranked_campaigns["cpc"] = ranked_campaigns["spend"].div(ranked_campaigns["clicks"])' in SOURCE


def test_results_schema_change_invalidates_and_migrates_cached_frames():
    assert "DASHBOARD_CACHE_VERSION = 2" in SOURCE
    assert 'schema_key = ("schema", DASHBOARD_CACHE_VERSION, selected_platform_key, api_key)' in SOURCE
    assert "query_key = (\n    DASHBOARD_CACHE_VERSION," in SOURCE
    assert "if active_query_key[0] != DASHBOARD_CACHE_VERSION:" in SOURCE
    assert 'frame["results"] = frame.get("__results__", 0)' in SOURCE
    assert 'frame["cost_per_result"] = 0.0' in SOURCE


def test_historical_charts_are_commented_out():
    active_strings = {
        node.value
        for node in ast.walk(ast.parse(SOURCE))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }

    assert "### Tendencias Históricas" not in active_strings
    assert "#### Inversión vs. conversiones diarias (eje dual)" not in active_strings
    assert "#### Distribución de Conversiones por Campaña" not in active_strings
    assert '# st.markdown("### Tendencias Históricas")' in SOURCE
    assert "# col_chart_left, col_chart_right = st.columns(2)" in SOURCE


if __name__ == "__main__":
    test_dashboard_has_light_dark_and_spanish_meta_labels()
    test_theme_change_does_not_refetch_official_meta_data()
    test_charts_and_header_follow_selected_theme()
    test_dashboard_hashtag_ranking_uses_returned_post_text()
    test_regions_are_localized_and_charted()
    test_campaign_names_are_cleaned_for_display()
    test_sidebar_actions_are_ordered_without_a_separator()
    test_ads_cards_show_real_leads_and_total_reach()
    test_featured_campaigns_show_requested_meta_metrics()
    test_results_schema_change_invalidates_and_migrates_cached_frames()
    test_historical_charts_are_commented_out()
