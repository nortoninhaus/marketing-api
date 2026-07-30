import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
import pandas as pd
import requests
from streamlit.testing.v1 import AppTest

from dashboard.api import process_api_response
from dashboard.auth import create_dashboard_token
from dashboard import utils as dashboard_utils

DASHBOARD_PATH = Path(__file__).resolve().parents[1] / "dashboard.py"
SOURCE = DASHBOARD_PATH.read_text()
CONFIG_SOURCE = DASHBOARD_PATH.with_name("dashboard").joinpath("config.py").read_text()
API_SOURCE = DASHBOARD_PATH.with_name("dashboard").joinpath("api.py").read_text()
UTILS_SOURCE = DASHBOARD_PATH.with_name("dashboard").joinpath("utils.py").read_text()


def test_dashboard_has_light_dark_and_spanish_meta_labels():
    assert 'st.sidebar.button(theme_icon, key="theme_switch_button"' in SOURCE
    assert 'st.sidebar.radio("Tema", ["Claro", "Oscuro"]' not in SOURCE
    assert '"male": "Masculino"' in CONFIG_SOURCE
    assert '"female": "Femenino"' in CONFIG_SOURCE
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
    assert "effective_object_story_id" in API_SOURCE
    assert '"post_message": post_text' in API_SOURCE
    assert 'preview.get("body", "")' in SOURCE
    assert 'preview.get("post_message", "")' in SOURCE
    assert 'text_col = "caption" if "caption" in df_curr.columns else "campaign_name"' in SOURCE
    assert 're.findall(r"#[\\wáéíóúÁÉÍÓÚñÑ]+", text)' in SOURCE
    assert "No se encontraron hashtags" not in SOURCE


def test_regions_are_localized_and_charted():
    assert "clean_region_name" in SOURCE
    assert 're.sub(r"\\s+Province$"' in UTILS_SOURCE
    assert 'st.markdown("#### Regiones principales")' in SOURCE
    assert "region_chart" in SOURCE


def test_campaign_previews_are_cleaned_but_reporting_keeps_full_names():
    assert "clean_campaign_name" in UTILS_SOURCE
    assert '"campaign_label": clean_campaign_name(campaign_name)' in API_SOURCE
    assert '"base_campaign_name": "Campaña"' in SOURCE
    assert "campaign_name = html.escape(str(row.base_campaign_name))" in SOURCE


def test_sidebar_actions_are_ordered_without_a_separator():
    query_button = 'st.sidebar.button("🚀 Consultar API"'
    logout_button = 'st.sidebar.button("🔒 Cerrar Sesión"'

    assert SOURCE.index(query_button) < SOURCE.index(logout_button)
    assert 'st.sidebar.markdown("---")' not in SOURCE
    assert ".inhaus-logout-container {" not in SOURCE


def test_meta_filters_use_unique_campaigns_and_multiple_adsets():
    assert "campaign_options = sorted({" in SOURCE
    assert 'st.multiselect("Conjuntos de anuncios", adset_options, key="meta_adset_filter")' in SOURCE
    assert 'filtered_meta_rows["adset_name"].isin(adset_filter)' in SOURCE


def test_meta_base_campaign_name_strips_publisher_platform_suffixes():
    campaign_name = "BAJAJ / Mayoristas / ALCANCE / JULIO 2026"

    assert {
        dashboard_utils.meta_base_campaign_name(name)
        for name in (
            campaign_name,
            f"{campaign_name}_facebook",
            f"{campaign_name}_instagram",
            f"{campaign_name}_audience_network",
            f"{campaign_name}_messenger",
            f"{campaign_name}_whatsapp",
            f"{campaign_name}_unknown",
        )
    } == {campaign_name}


def test_dashboard_filters_accept_multiple_adsets():
    frame = pd.DataFrame({
        "campaign_name": ["Campaign"] * 3,
        "adset_name": ["Set A", "Set B", "Set C"],
        "ad_name": ["Ad A", "Ad B", "Ad C"],
    })

    result = dashboard_utils.apply_dashboard_filters(
        frame,
        campaign_filter=[],
        adset_filter=["Set A", "Set C"],
        ad_filter="Todos",
    )

    assert result["adset_name"].tolist() == ["Set A", "Set C"]


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
    assert 'standard_metrics = ["impressions", "clicks", "spend", "conversions", "lead", "reach", "post_engagement", "__results__", "cost_per_result"]' in SOURCE
    assert 'curr_primary = df_curr["lead"].sum()' in SOURCE
    assert 'primary_label = "Clientes Potenciales"' in SOURCE
    assert 'get_kpi_card_html("Alcance Total", f"{total_reach_curr:,}"' in SOURCE
    assert '"Costo por Conversión (CPA)"' not in SOURCE


def test_meta_post_engagement_is_requested_and_normalized():
    df = process_api_response(
        [{
            "campaign_name": "Engagement Campaign",
            "date": "2026-07-01",
            "metrics": {"post_engagement": 37},
        }],
        "meta_ads",
        "client_1",
        "user_1",
    )

    assert df.loc[0, "post_engagement"] == 37
    assert '"post_engagement"' in SOURCE[
        SOURCE.index("standard_metrics ="):SOURCE.index("query_configs.append")
    ]


def test_previous_month_fetch_uses_configured_campaign_timeout():
    previous_month_fetch = SOURCE[
        SOURCE.index("prev_rows = fetch_campaign_data_from_api("):
        SOURCE.index("if curr_rows:")
    ]

    assert "timeout=45" not in previous_month_fetch
    assert "timeout=CAMPAIGN_DATA_TIMEOUT" in API_SOURCE


def test_ads_campaign_table_preserves_post_engagement_for_rankings():
    campaign_table_source = SOURCE[
        SOURCE.index("df_table = df_curr.copy()"):SOURCE.index("meta_table =")
    ]

    assert '"post_engagement": "sum"' in campaign_table_source


def test_featured_campaigns_show_requested_meta_metrics():
    df = process_api_response(
        [{
            "campaign_name": "Lead campaign",
            "date": "2026-07-01",
            "metrics": {
                "result_indicator": "reach",
                "__results__": 7,
                "cost_per_result": 0.42,
                "lead": 3,
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
    assert df.loc[0, "result_indicator"] == "reach"
    assert '"__results__"' in SOURCE
    featured_campaign_source = SOURCE[
        SOURCE.index("campaign_summary ="):
        SOURCE.index("preview_names =")
    ]
    for label in (
        "Tipo de resultado",
        "Resultados",
        "Costo por resultado",
        "CPM",
        "Impresiones",
        "Clics",
        "CPC",
        "Inversión",
    ):
        assert f'"{label}"' in featured_campaign_source
    assert '"reach": "Reach"' not in featured_campaign_source
    assert '.sort_values(["results", "result_indicator"], ascending=[False, False])' in SOURCE
    assert 'campaign_summary["result_label"] = campaign_summary["result_indicator"].apply(translate_meta_result_indicator)' in SOURCE
    assert '"base_campaign_name": "Campaña"' in featured_campaign_source
    assert "campaign_summary = ranked_campaigns" not in featured_campaign_source
    assert 'groupby("base_campaign_name").agg({' in featured_campaign_source
    assert '"result_indicator": "first"' in featured_campaign_source
    assert '"platform": "Plataforma"' not in featured_campaign_source


def test_meta_campaign_cards_render_three_top_three_rankings():
    assert "ranking_specs = (" in SOURCE
    ranking_source = SOURCE[
        SOURCE.index("ranking_specs ="):SOURCE.index("for preview in previews:")
    ]

    for title, metric, label in (
        ("clientes potenciales", "lead", "Clientes potenciales"),
        ("alcance", "reach", "Alcance"),
        ("interacciones", "post_engagement", "Interacciones"),
    ):
        assert f'("{title}", "{metric}", "{label}")' in ranking_source

    assert ".sort_values(metric, ascending=False).head(3)" in ranking_source
    assert "rank_cols = st.columns(3)" in ranking_source
    assert "metric_rows = [(metric_label," in ranking_source
    assert 'st.markdown(f"### Ranking: top campañas por {ranking_name} (Meta)")' in ranking_source
    assert "campaign_name = html.escape(str(row.base_campaign_name))" in ranking_source


def test_meta_result_indicator_survives_dashboard_normalization():
    df = process_api_response(
        [{
            "campaign_name": "Reach Campaign",
            "date": "2026-07-01",
            "metrics": {
                "result_indicator": "reach",
                "__results__": 42_206,
                "cost_per_result": 0.01,
            },
        }],
        "meta_ads",
        "client_1",
        "user_1",
    )

    assert df.loc[0, "result_indicator"] == "reach"


@pytest.mark.parametrize(("indicator", "label"), [
    ("reach", "Alcance"),
    ("actions:lead", "Clientes potenciales"),
    ("actions:post_engagement", "Interacciones con la publicación"),
    ("actions:landing_page_view", "Visitas a la página de destino"),
    ("actions:link_click", "Clics en el enlace"),
    ("actions:purchase", "Compras"),
])
def test_meta_result_indicators_use_official_labels(indicator, label):
    assert dashboard_utils.translate_meta_result_indicator(indicator) == label


def test_unknown_meta_result_indicator_is_not_humanized():
    assert dashboard_utils.translate_meta_result_indicator("actions:future_metric") == "—"


def test_results_schema_change_invalidates_and_migrates_cached_frames():
    assert "DASHBOARD_CACHE_VERSION = 4" in SOURCE
    assert 'schema_key = ("schema", DASHBOARD_CACHE_VERSION, selected_platform_key, api_key)' in SOURCE
    assert "query_key = (\n    DASHBOARD_CACHE_VERSION," in SOURCE
    assert "if active_query_key[0] != DASHBOARD_CACHE_VERSION:" in SOURCE
    assert 'frame["results"] = frame.get("__results__", 0)' in SOURCE
    assert 'frame["cost_per_result"] = 0.0' in SOURCE
    assert 'frame["result_indicator"] = ""' in SOURCE
    assert 'frame["post_engagement"] = 0' in SOURCE


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
