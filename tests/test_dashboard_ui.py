import ast
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import pandas as pd
import requests
from streamlit.testing.v1 import AppTest

from dashboard import api as dashboard_api
from dashboard.api import process_api_response
from dashboard.auth import create_dashboard_token
from dashboard import ui as dashboard_ui
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


def test_light_theme_styles_streamlit_expand_sidebar_button():
    assert (
        '[data-testid="stExpandSidebarButton"],\n'
        '    [data-testid="stExpandSidebarButton"] *,'
    ) in SOURCE


def test_dashboard_hashtag_ranking_uses_returned_post_text():
    assert "ad_hashtag_rows" in SOURCE
    assert "effective_object_story_id" in API_SOURCE
    assert '"post_message": post_text' in API_SOURCE
    assert 'preview.get("body", "")' in SOURCE
    assert 'preview.get("post_message", "")' in SOURCE
    assert 'text_col = "caption" if "caption" in df_curr.columns else "campaign_name"' in SOURCE
    assert 're.findall(r"#[\\wáéíóúÁÉÍÓÚñÑ]+", text)' in SOURCE
    assert 'for preview in {p["ad_id"]: p for p in previews}.values():' in SOURCE
    assert "No se encontraron hashtags" not in SOURCE


def test_regions_are_localized_and_charted():
    assert "clean_region_name" in SOURCE
    assert 're.sub(r"\\s+Province$"' in UTILS_SOURCE
    assert 'st.markdown("#### Regiones principales")' in SOURCE
    assert "region_chart" in SOURCE


def test_campaign_previews_are_cleaned_but_reporting_keeps_full_names():
    assert "clean_campaign_name" in UTILS_SOURCE
    assert '"campaign_label": clean_campaign_name(campaign_name)' in API_SOURCE
    assert '("base_campaign_name", "Campaña")' in SOURCE
    assert "campaign_name = html.escape(str(row.base_campaign_name))" in SOURCE


def test_meta_aggregate_insights_preserves_reach_and_paginates_actions(monkeypatch):
    responses = [
        {
            "data": [{
                "campaign_name": "Campaign",
                "ad_id": "ad-1",
                "ad_name": "First",
                "impressions": "100",
                "reach": "80",
                "results": [{
                    "indicator": "actions:lead",
                    "values": [{"value": "5"}],
                }],
                "cost_per_result": [{
                    "indicator": "actions:lead",
                    "values": [{"value": "12.34"}],
                }],
                "actions": [
                    {"action_type": "lead", "value": "5"},
                    {"action_type": "post_engagement", "value": "7"},
                ],
            }],
            "paging": {"cursors": {"after": "next-page"}},
        },
        {
            "data": [{
                "campaign_name": "Campaign",
                "ad_id": "ad-2",
                "ad_name": "Second",
                "impressions": "50",
                "reach": "45",
                "actions": [],
            }],
        },
    ]
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(kwargs["json"])
        return SimpleNamespace(status_code=200, json=lambda: responses[len(calls) - 1])

    monkeypatch.setattr(dashboard_api.requests, "post", fake_post)

    rows, error = dashboard_api.fetch_meta_aggregate_insights(
        "client_1",
        "123",
        date(2026, 7, 1),
        date(2026, 7, 31),
        "ad",
        {"campaign.id": ["campaign-1"]},
        "api-key",
    )

    assert error is None
    assert [row["ad_id"] for row in rows] == ["ad-1", "ad-2"]
    assert rows[0]["reach"] == 80
    assert rows[0]["lead"] == 5
    assert rows[0]["post_engagement"] == 7
    assert rows[0]["result_indicator"] == "actions:lead"
    assert rows[0]["results"] == 5.0
    assert rows[0]["cost_per_result"] == 12.34
    requested_fields = calls[0]["params"]["fields"].split(",")
    assert "results" in requested_fields
    assert "cost_per_result" in requested_fields
    assert "adset_id" in requested_fields
    assert "adset_name" in requested_fields
    assert calls[0]["params"]["level"] == "ad"
    assert "time_increment" not in calls[0]["params"]
    assert "breakdowns" not in calls[0]["params"]
    assert calls[1]["params"]["after"] == "next-page"


def test_meta_filter_rows_include_normalized_campaign_and_adset_budgets(monkeypatch):
    dashboard_api.fetch_meta_filter_rows.clear()
    payload = {
        "data": [{
            "id": "ad-1",
            "name": "Ad One",
            "campaign": {
                "id": "campaign-1",
                "name": "Campaign One",
                "daily_budget": "0",
                "lifetime_budget": "125000",
            },
            "adset": {
                "id": "adset-1",
                "name": "Set One",
                "daily_budget": "5000",
                "lifetime_budget": "0",
            },
        }],
    }
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(kwargs["json"])
        return SimpleNamespace(status_code=200, json=lambda: payload)

    monkeypatch.setattr(dashboard_api.requests, "post", fake_post)

    rows, error = dashboard_api.fetch_meta_filter_rows(
        "budget-client", "budget-account", "budget-key"
    )

    assert error is None
    assert rows[0]["campaign_lifetime_budget"] == 1250.0
    assert rows[0]["campaign_daily_budget"] == 0.0
    assert rows[0]["adset_lifetime_budget"] == 0.0
    assert rows[0]["adset_daily_budget"] == 50.0
    fields = calls[0]["params"]["fields"]
    assert "campaign{id,name,daily_budget,lifetime_budget}" in fields
    assert "adset{id,name,daily_budget,lifetime_budget}" in fields


def test_targeted_meta_ad_previews_use_requested_ad_id(monkeypatch):
    def fake_post(*args, **kwargs):
        path = kwargs["json"]["path"]
        if path == "ad-2":
            payload = {
                "id": "ad-2",
                "name": "Winning ad",
                "campaign": {"name": "Campaign"},
                "creative": {
                    "effective_object_story_id": "post-2",
                    "object_story_spec": {
                        "message": "Story text",
                        "link_data": {"message": "Creative text"},
                    },
                },
            }
        elif path == "ad-2/previews":
            payload = {"data": [{"body": "<div>Winning preview</div>"}]}
        else:
            payload = {"message": "Published text"}
        return SimpleNamespace(status_code=200, json=lambda: payload)

    monkeypatch.setattr(dashboard_api.requests, "post", fake_post)

    previews, error = dashboard_api.fetch_meta_ad_previews(
        "client_1",
        "123",
        (("lead", "Campaign", "ad-2", "Winning ad"),),
        "api-key",
    )

    assert error is None
    assert previews == [{
        "ranking_metric": "lead",
        "campaign_name": "Campaign",
        "campaign_label": dashboard_utils.clean_campaign_name("Campaign"),
        "ad_id": "ad-2",
        "ad_name": "Winning ad",
        "body": "<div>Winning preview</div>",
        "post_message": "Story text Creative text Published text",
    }]


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


def test_campaign_filters_trigger_scoped_meta_detail_fetch():
    detail_fetch_source = SOURCE[
        SOURCE.index("detail_curr_rows = []"):
        SOURCE.index("current_account_insights = []")
    ]

    assert 'if applied_campaign_filter or applied_adset_filter or applied_ad_filter != "Todos":' in detail_fetch_source
    assert "detail_curr_rows, detail_prev_rows = fetch_meta_detail_rows(" in detail_fetch_source
    assert 'active_context.get("opt_filters", {})' in detail_fetch_source


def test_meta_detail_fetch_calls_once_per_period_and_keeps_campaign_scope():
    calls = []

    def fetch(*args, **kwargs):
        calls.append((args, kwargs))
        return []

    dashboard_utils.fetch_meta_detail_rows(
        fetch,
        "meta_ads",
        "client_1",
        "user_1",
        "account_1",
        date(2026, 7, 1),
        date(2026, 7, 31),
        date(2026, 6, 1),
        date(2026, 6, 30),
        ["impressions"],
        ["campaign_name"],
        {"filters": {"campaign.id": ["campaign_1"]}},
        [],
        "Todos",
        pd.DataFrame(),
        pd.DataFrame(),
        "api-key",
    )

    assert len(calls) == 2
    assert all(call[0][7][-2:] == ["adset_name", "ad_name"] for call in calls)
    assert all(call[0][8]["filters"] == {"campaign.id": ["campaign_1"]} for call in calls)


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


@pytest.mark.parametrize(("level", "metadata", "expected"), [
    ("campaign", {"campaign_lifetime_budget": 1250.0}, ("$1,250.00", 1250.0)),
    ("campaign", {"campaign_daily_budget": 50.0}, ("Presupuesto diario", 0.0)),
    ("campaign", {}, ("Se administra a nivel de conjuntos", 0.0)),
    ("adset", {"adset_lifetime_budget": 800.0}, ("$800.00", 800.0)),
    ("adset", {"adset_daily_budget": 25.0}, ("Presupuesto diario", 0.0)),
    ("adset", {}, ("Se administra a nivel campaña", 0.0)),
    ("ad", {"adset_daily_budget": 25.0}, ("Se administra a nivel de conjuntos", 0.0)),
    ("ad", {}, ("Se administra a nivel campaña", 0.0)),
    ("campaign", None, ("N/D", 0.0)),
])
def test_meta_budget_display_follows_owner_level(level, metadata, expected):
    assert dashboard_utils.meta_budget_display(level, metadata) == expected


def test_meta_summary_enrichment_uses_native_cost_and_budget_metadata():
    frame = pd.DataFrame({
        "base_campaign_name": ["Campaign A", "Campaign B"],
        "cost_per_result": [999.0, 999.0],
    })
    aggregate_rows = [{
        "campaign_name": "Campaign A",
        "result_indicator": "actions:lead",
        "cost_per_result": 12.34,
    }]
    filter_rows = [
        {"campaign_name": "Campaign A", "campaign_lifetime_budget": 1250.0},
        {"campaign_name": "Campaign B", "campaign_daily_budget": 50.0},
    ]

    result = dashboard_utils.enrich_meta_campaign_summary(
        frame, aggregate_rows, filter_rows, "campaign"
    )

    assert result.loc[0, "cost_per_result"] == 12.34
    assert pd.isna(result.loc[1, "cost_per_result"])
    assert result["budget_display"].tolist() == ["$1,250.00", "Presupuesto diario"]
    assert result["budget_total"].tolist() == [1250.0, 0.0]


@pytest.mark.parametrize("summary_name", [
    "Campaign_Audience",
    "Campaign_Audience_18-24",
    "Campaign_Audience_18-24_facebook",
])
def test_meta_summary_enrichment_uses_exact_or_longest_known_campaign(summary_name):
    frame = pd.DataFrame({"base_campaign_name": [summary_name]})
    aggregate_rows = [
        {"campaign_id": "target", "campaign_name": "Campaign_Audience", "cost_per_result": 7.5},
        {"campaign_id": "prefix", "campaign_name": "Campaign", "cost_per_result": 1.0},
    ]
    filter_rows = [
        {"campaign_id": "other", "campaign_name": "Campaign_Audience", "campaign_lifetime_budget": 999.0},
        {"campaign_id": "target", "campaign_name": "Campaign_Audience", "campaign_lifetime_budget": 640.0, "ad_id": "1"},
        {"campaign_id": "target", "campaign_name": "Campaign_Audience", "campaign_lifetime_budget": 640.0, "ad_id": "2"},
    ]

    for rows in (filter_rows, list(reversed(filter_rows))):
        result = dashboard_utils.enrich_meta_campaign_summary(
            frame, aggregate_rows, rows, "campaign"
        )
        assert tuple(result.loc[0, [
            "cost_per_result", "budget_display", "budget_total"
        ]]) == (7.5, "$640.00", 640.0)


@pytest.mark.parametrize(
    ("level", "frame_row", "name_fields", "id_field"),
    [
        (
            "campaign",
            {"base_campaign_name": "Shared"},
            {"campaign_name": "Shared"},
            "campaign_id",
        ),
        (
            "campaign",
            {"base_campaign_name": "Shared"},
            {"campaign_name": "Shared"},
            None,
        ),
        (
            "adset",
            {"base_campaign_name": "Campaign", "adset_name": "Shared"},
            {"campaign_name": "Campaign", "adset_name": "Shared"},
            "adset_id",
        ),
        (
            "ad",
            {"adset_name": "Shared Set", "ad_name": "Shared"},
            {"adset_name": "Shared Set", "ad_name": "Shared"},
            "ad_id",
        ),
    ],
    ids=["campaign-ids", "campaign-no-ids", "adset-ids", "ad-ids"],
)
def test_meta_summary_enrichment_returns_unavailable_for_ambiguous_identity(
    level, frame_row, name_fields, id_field
):
    identities = ({id_field: "entity-1"}, {id_field: "entity-2"}) if id_field else ({}, {})
    aggregate_rows = [
        {**name_fields, **identities[0], "cost_per_result": 2.0},
        {**name_fields, **identities[1], "cost_per_result": 9.0},
    ]
    filter_rows = [
        {
            **name_fields,
            **identities[0],
            "campaign_lifetime_budget": 100.0,
            "adset_lifetime_budget": 100.0,
        },
        {
            **name_fields,
            **identities[1],
            "campaign_lifetime_budget": 200.0,
            "adset_lifetime_budget": 200.0,
        },
    ]

    result = dashboard_utils.enrich_meta_campaign_summary(
        pd.DataFrame([frame_row]), aggregate_rows, filter_rows, level
    )

    assert pd.isna(result.loc[0, "cost_per_result"])
    assert result.loc[0, "budget_display"] == "N/D"
    assert result.loc[0, "budget_total"] == 0.0


@pytest.mark.parametrize(
    (
        "level", "frame_row", "name_fields", "id_field",
        "target_budget", "other_budget", "expected_budget",
    ),
    [
        (
            "adset",
            {"base_campaign_name": "Campaign", "adset_name": "Shared Set"},
            {"campaign_name": "Campaign", "adset_name": "Shared Set"},
            "adset_id",
            {"adset_lifetime_budget": 800.0},
            {"adset_daily_budget": 5.0},
            ("$800.00", 800.0),
        ),
        (
            "ad",
            {"adset_name": "Shared Set", "ad_name": "Shared Ad"},
            {"adset_name": "Shared Set", "ad_name": "Shared Ad"},
            "ad_id",
            {"adset_daily_budget": 25.0},
            {},
            ("Se administra a nivel de conjuntos", 0.0),
        ),
    ],
    ids=["adset", "ad"],
)
def test_meta_summary_enrichment_uses_detail_id_for_budget_metadata(
    level, frame_row, name_fields, id_field,
    target_budget, other_budget, expected_budget,
):
    aggregate_rows = [{**name_fields, id_field: "target", "cost_per_result": 4.5}]
    filter_rows = [
        {**name_fields, id_field: "other", **other_budget},
        {**name_fields, id_field: "target", **target_budget},
    ]
    for rows in (filter_rows, list(reversed(filter_rows))):
        result = dashboard_utils.enrich_meta_campaign_summary(
            pd.DataFrame([frame_row]), aggregate_rows, rows, level
        )
        assert result.loc[0, "cost_per_result"] == 4.5
        assert tuple(result.loc[0, ["budget_display", "budget_total"]]) == expected_budget


def test_meta_campaigns_with_impressions_uses_positive_campaign_total():
    frame = pd.DataFrame({
        "campaign_name": [
            "Delivered_facebook",
            "Delivered_instagram",
            "Empty_facebook",
        ],
        "impressions": [0, 12, 0],
    })

    assert dashboard_utils.meta_campaigns_with_impressions(frame) == {"Delivered"}


def test_select_meta_ad_winners_uses_each_ranking_metric():
    rows = [
        {
            "campaign_name": "Campaign",
            "ad_id": "2",
            "impressions": 100,
            "lead": 9,
            "reach": 20,
            "post_engagement": 1,
        },
        {
            "campaign_name": "Campaign",
            "ad_id": "1",
            "impressions": 200,
            "lead": 2,
            "reach": 80,
            "post_engagement": 7,
        },
    ]
    ranked = {
        "lead": ["Campaign"],
        "reach": ["Campaign"],
        "post_engagement": ["Campaign"],
    }

    winners = dashboard_utils.select_meta_ad_winners(rows, ranked)

    assert winners[("lead", "Campaign")]["ad_id"] == "2"
    assert winners[("reach", "Campaign")]["ad_id"] == "1"
    assert winners[("post_engagement", "Campaign")]["ad_id"] == "1"


def test_campaign_total_row_uses_sums_and_average_cost():
    frame = pd.DataFrame({
        "result_indicator": ["actions:lead", "actions:lead"],
        "result_label": ["Clientes potenciales", "Clientes potenciales"],
        "results": [10, 30],
        "cost_per_result": [2, 4],
        "budget_total": [1000.0, 250.0],
        "spend": [80, 120],
        "impressions": [4_000, 6_000],
        "clicks": [200, 300],
    })

    row = dashboard_utils.build_meta_campaign_total_row(frame)

    assert row == {
        "Campaña": "TOTAL",
        "Tipo de resultado": "",
        "Resultados": "40",
        "Costo por resultado": "$3.00",
        "Presupuesto": "$1,250.00",
        "CPM": "$20.00",
        "Impresiones": "10,000",
        "Clics": "500",
        "CPC": "$0.40",
        "Importe gastado": "$200.00",
    }


def test_campaign_total_row_sums_mixed_results_and_averages_cost():
    frame = pd.DataFrame({
        "result_indicator": ["actions:lead", "reach"],
        "result_label": ["Clientes potenciales", "Alcance"],
        "results": [10, 1_000],
        "cost_per_result": [2, 4],
        "budget_total": [1000.0, 250.0],
        "spend": [80, 120],
        "impressions": [4_000, 6_000],
        "clicks": [200, 300],
    })

    row = dashboard_utils.build_meta_campaign_total_row(frame)

    assert row["Tipo de resultado"] == ""
    assert row["Resultados"] == "1,010"
    assert row["Costo por resultado"] == "$3.00"


def test_meta_detail_table_config_follows_applied_filter_hierarchy():
    columns = {"base_campaign_name", "adset_name", "ad_name"}

    assert dashboard_utils.meta_detail_table_config(
        [], [], "Todos", columns
    ) == (
        (("base_campaign_name", "Campaña"),),
        "Detalle de Campañas y Resultados",
    )
    assert dashboard_utils.meta_detail_table_config(
        ["Campaign A", "Campaign B"], [], "Todos", columns
    ) == (
        (
            ("base_campaign_name", "Campaña"),
            ("adset_name", "Conjunto de anuncios"),
        ),
        "Detalle de Conjuntos de anuncios y Resultados",
    )
    assert dashboard_utils.meta_detail_table_config(
        ["Campaign A"], ["Set A", "Set B"], "Todos", columns
    ) == (
        (
            ("adset_name", "Conjunto de anuncios"),
            ("ad_name", "Anuncio"),
        ),
        "Detalle de Anuncios y Resultados",
    )
    assert dashboard_utils.meta_detail_table_config(
        ["Campaign A"], [], "Ad A", columns
    )[0] == (
        ("adset_name", "Conjunto de anuncios"),
        ("ad_name", "Anuncio"),
    )


def test_meta_detail_table_config_falls_back_when_child_columns_are_missing():
    assert dashboard_utils.meta_detail_table_config(
        ["Campaign A"], ["Set A"], "Todos", {"base_campaign_name"}
    ) == (
        (("base_campaign_name", "Campaña"),),
        "Detalle de Campañas y Resultados",
    )


def test_campaign_total_row_supports_two_identity_columns():
    frame = pd.DataFrame({
        "results": [10, 30],
        "cost_per_result": [2, 4],
        "budget_total": [1000.0, 250.0],
        "spend": [80, 120],
        "impressions": [4_000, 6_000],
        "clicks": [200, 300],
    })

    row = dashboard_utils.build_meta_campaign_total_row(
        frame,
        identity_labels=("Campaña", "Conjunto de anuncios"),
    )

    assert list(row)[:3] == [
        "Campaña",
        "Conjunto de anuncios",
        "Tipo de resultado",
    ]
    assert row["Campaña"] == "TOTAL"
    assert row["Conjunto de anuncios"] == ""


def test_theme_table_merges_total_label_across_two_columns(monkeypatch):
    rendered = []
    monkeypatch.setattr(
        dashboard_ui.st,
        "markdown",
        lambda value, **kwargs: rendered.append(value),
    )

    dashboard_ui.show_theme_table(
        pd.DataFrame([{
            "Campaña": "TOTAL",
            "Tipo de resultado": "",
            "Resultados": "40",
        }]),
        merge_total_cells=True,
    )

    assert '<td colspan="2">TOTAL</td>' in rendered[0]


def test_campaign_total_row_is_appended_after_formatted_campaigns():
    total_append = "pd.concat([campaign_summary, pd.DataFrame([total_row])], ignore_index=True)"
    total_render = "show_theme_table(campaign_summary, merge_total_cells=True)"
    assert total_append in SOURCE
    assert total_render in SOURCE
    assert SOURCE.index(total_append) < SOURCE.index(total_render)


def test_meta_detail_table_uses_dynamic_identity_columns():
    resolution_source = SOURCE[
        SOURCE.index('identity_config = (("base_campaign_name", "Campaña"),)'):
        SOURCE.index("current_account_insights =")
    ]
    detail_source = SOURCE[
        SOURCE.index("# CAMPAIGN BREAKDOWN TABLE"):
        SOURCE.index("ranking_specs = (")
    ]

    assert "meta_detail_table_config(" in resolution_source
    assert "applied_campaign_filter" in resolution_source
    assert "applied_adset_filter" in resolution_source
    assert "applied_ad_filter" in resolution_source
    assert "groupby(identity_sources)" in detail_source
    assert "dict(identity_config)" in detail_source
    assert "build_meta_campaign_total_row(" in detail_source
    assert "identity_labels=identity_labels" in detail_source
    assert 'st.markdown(f"### {detail_title}")' in detail_source
    assert 'csv_export_frame["frame"] = campaign_summary' in detail_source


def test_delivered_meta_campaigns_filter_all_meta_views():
    eligibility_source = SOURCE[
        SOURCE.index("eligible_campaigns = meta_campaigns_with_impressions(df_curr)"):
        SOURCE.index("# Inject JavaScript")
    ]
    assert "eligible_previous_campaigns = meta_campaigns_with_impressions(df_prev)" in eligibility_source
    assert 'df_curr["campaign_name"].astype(str).apply(meta_base_campaign_name)' in eligibility_source
    assert ".isin(eligible_campaigns)" in eligibility_source
    assert "if not df_prev.empty:" in eligibility_source


def test_aggregate_meta_reach_uses_entity_level_rows():
    assert 'fetch_meta_aggregate_insights(' in SOURCE
    assert '"account"' in SOURCE
    assert '"campaign"' in SOURCE
    assert '"ad"' in SOURCE
    assert "total_reach_curr = current_account_insights[0][\"reach\"]" in SOURCE
    assert "campaign_reach_by_name" in SOURCE
    assert 'campaign_ranking_summary["reach"]' in SOURCE


def test_lead_summary_cost_and_spend_render_together():
    assert "lead_cost_per_result = total_spend_curr / curr_primary" in SOURCE
    assert "Costo por resultado" in SOURCE
    assert "Importe gastado" in SOURCE


def test_metric_specific_preview_uses_ad_winners():
    assert "select_meta_ad_winners(" in SOURCE
    assert "fetch_meta_ad_previews(" in SOURCE
    assert 'previews_by_campaign = {' in SOURCE
    assert '(p["ranking_metric"], p["campaign_name"])' in SOURCE
    assert "previews_by_campaign.get((metric, row.base_campaign_name))" in SOURCE
    assert 'preview["body"] if preview and preview.get("body") else' in SOURCE


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
    assert 'get_kpi_card_html("Alcance Total", reach_value' in SOURCE
    assert 'total_reach_curr = current_account_insights[0]["reach"]' in SOURCE
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
        SOURCE.index("ranking_specs =")
    ]
    for label in (
        "Tipo de resultado",
        "Resultados",
        "Costo por resultado",
        "CPM",
        "Impresiones",
        "Clics",
        "CPC",
        "Presupuesto",
        "Importe gastado",
    ):
        assert f'"{label}"' in featured_campaign_source
    assert '"reach": "Reach"' not in featured_campaign_source
    assert '.sort_values(["results", "result_indicator"], ascending=[False, False])' in SOURCE
    assert 'campaign_summary["result_label"] = campaign_summary["result_indicator"].apply(translate_meta_result_indicator)' in SOURCE
    assert "**dict(identity_config)" in featured_campaign_source
    assert "campaign_summary = ranked_campaigns" not in featured_campaign_source
    assert ".groupby(identity_sources).agg({" in featured_campaign_source
    assert '"result_indicator": "first"' in featured_campaign_source
    assert '"platform": "Plataforma"' not in featured_campaign_source


def test_meta_table_uses_native_period_cost_and_level_budget():
    table_source = SOURCE[
        SOURCE.index("# CAMPAIGN BREAKDOWN TABLE"):
        SOURCE.index("ranking_specs =")
    ]
    column_source = table_source[
        table_source.index("campaign_summary = campaign_summary["):
        table_source.index("].rename(columns={")
    ]

    assert "enrich_meta_campaign_summary(" in table_source
    assert "result_cost_weighted" not in table_source
    assert '"budget_display": "Presupuesto"' in table_source
    assert '"spend": "Importe gastado"' in table_source
    assert column_source.index('"budget_display"') < column_source.index('"spend"')
    assert "adset_aggregate_insights" in SOURCE


def test_meta_ad_aggregate_request_uses_applied_filters():
    request_source = SOURCE[
        SOURCE.index("aggregate_requests ="):
        SOURCE.index("for insight_level, period_start, period_end")
    ]

    assert (
        '("ad", start_date, end_date, ad_aggregate_insights, '
        'applied_aggregate_filters)'
    ) in request_source


def test_meta_campaign_aggregate_request_uses_applied_filters():
    request_source = SOURCE[
        SOURCE.index("aggregate_requests ="):
        SOURCE.index("for insight_level, period_start, period_end")
    ]

    assert (
        '("campaign", start_date, end_date, campaign_aggregate_insights, '
        'applied_aggregate_filters)'
    ) in request_source


def test_meta_aggregate_level_follows_resolved_table_identity():
    resolution_index = SOURCE.index("meta_detail_table_config(")
    request_index = SOURCE.index("aggregate_requests =")
    table_source = SOURCE[
        SOURCE.index("# CAMPAIGN BREAKDOWN TABLE"):
        SOURCE.index("ranking_specs =")
    ]

    assert SOURCE.count("meta_detail_table_config(") == 1
    assert resolution_index < request_index
    assert '"base_campaign_name": "campaign"' in SOURCE[resolution_index:request_index]
    assert '}[identity_config[-1][0]]' in SOURCE[resolution_index:request_index]
    assert "meta_detail_table_config(" not in table_source


def test_meta_campaign_cards_render_three_top_three_rankings():
    assert "ranking_specs = (" in SOURCE
    ranking_source = SOURCE[
        SOURCE.index("ranking_specs ="):
        SOURCE.index('for preview in {p["ad_id"]: p for p in previews}.values():')
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
