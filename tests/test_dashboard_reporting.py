from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess

import pandas as pd
import pytest

from dashboard.api import process_api_response
from dashboard import reporting
from dashboard.reporting import build_report_payload, render_report, safe_asset_url


def _context(*connections):
    return {
        "connections": list(connections),
        "platform_configs": [
            {
                "platform_key": connection["platform"],
                "platform_label": connection["platform"].replace("_", " ").title(),
                "account_id": connection["account_id"],
                "metrics_list": [{"name": name} for name in ("spend", "impressions", "clicks", "custom_value")],
                "opt_filters": {},
            }
            for connection in connections
        ],
        "start_date": date(2026, 7, 1),
        "end_date": date(2026, 7, 31),
        "previous_start_date": date(2026, 6, 1),
        "previous_end_date": date(2026, 6, 30),
        "filters": {"campaign": ["Launch"]},
        "required_metrics": ["spend", "impressions", "clicks", "custom_value"],
    }


def _row(platform, spend, impressions, clicks, **metrics):
    source_metrics = {"spend": spend, "impressions": impressions, "clicks": clicks, **metrics}
    return {
        "source_platform": platform,
        "platform": platform,
        "campaign_name": f"{platform} launch",
        "date": pd.Timestamp("2026-07-01"),
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "source_metrics": source_metrics,
    }


def test_payload_keeps_named_account_context_dynamic_metrics_and_zero():
    current = pd.DataFrame([_row("meta_ads", 0, 100, 5, custom_value=17)])
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"})

    payload = build_report_payload("nutri", current, query_context=context)

    assert payload["meta"] == {
        "company_name": "Acme",
        "accounts": [{"account_id": "act_1", "name": "Acme", "platform": "meta_ads"}],
        "platforms": ["meta_ads"],
        "filters": {"campaign": ["Launch"]},
        "period": {"start": "2026-07-01", "end": "2026-07-31"},
        "previous_period": {"start": "2026-06-01", "end": "2026-06-30"},
        "generated_at": payload["meta"]["generated_at"],
    }
    assert payload["summary"]["spend"] == 0
    assert payload["summary"]["custom_value"] == 17
    assert payload["availability"]["metrics"]["spend"] is True
    assert payload["rows"]["current"][0]["source_metrics"]["custom_value"] == 17


def test_payload_uses_explicit_fallback_and_deterministic_multiple_names():
    current = pd.DataFrame([
        _row("meta_ads", 10, 100, 5),
        _row("google_ads", 20, 200, 10),
    ])
    context = _context(
        {"platform": "meta_ads", "account_id": "act_2"},
        {"platform": "google_ads", "account_id": "123", "display_name": "Beta"},
    )

    payload = build_report_payload("artz", current, query_context=context)

    assert payload["meta"]["company_name"] == "Meta Ads account act_2 + Beta"
    assert payload["meta"]["platforms"] == ["meta_ads", "google_ads"]
    assert payload["by_platform"]["meta_ads"]["spend"] == 10
    assert payload["by_platform"]["google_ads"]["spend"] == 20
    assert payload["rows"]["current"][0]["source_platform"] == "meta_ads"
    assert payload["rows"]["current"][1]["source_platform"] == "google_ads"


@pytest.mark.parametrize("template", ["nutri", "artz", "shamuna"])
def test_html_meta_publishers_keep_identity_and_route_to_facebook_or_instagram(template):
    current = pd.DataFrame([
        {**_row("meta_ads", 1, 10, 1), "publisher_platform": "audience_network"},
        {**_row("meta_ads", 2, 20, 2), "publisher_platform": "messenger"},
        {**_row("meta_ads", 3, 30, 3), "publisher_platform": "threads"},
    ])
    payload = build_report_payload(
        template,
        current,
        query_context=_context({"platform": "meta_ads", "account_id": "act_1"}),
    )
    compact_html = re.sub(r"\s+", "", render_report(template, payload))

    assert [row["publisher_platform"] for row in payload["rows"]["current"]] == [
        "audience_network",
        "messenger",
        "threads",
    ]
    assert 'source==="instagram"||source==="threads"' in compact_html
    assert 'isMeta(source)?metaPublisher(publisher||row.platform||source)' in compact_html


def test_html_content_rows_do_not_replace_publisher_metric_rows():
    current = pd.DataFrame([
        {**_row("meta_ads", 10, 100, 5), "publisher_platform": "facebook"},
        {**_row("meta_ads", 20, 200, 10), "publisher_platform": "instagram"},
    ])
    content_rows = [{
        "source_platform": "meta_ads",
        "publisher_platform": "facebook",
        "ad_id": "top-ad",
        "source_metrics": {"spend": 999, "impressions": 9999},
    }]

    payload = build_report_payload(
        "nutri",
        current,
        query_context=_context({"platform": "meta_ads", "account_id": "act_1"}),
        optional={"content_rows": content_rows},
    )

    assert payload["summary"]["spend"] == 30
    assert payload["summary"]["impressions"] == 300
    assert payload["rows"]["content"] == content_rows
    assert {row["publisher_platform"] for row in payload["rows"]["current"]} == {
        "facebook",
        "instagram",
    }


def test_payload_handles_previous_deltas_and_zero_denominator():
    current = pd.DataFrame([_row("meta_ads", 30, 150, 10)])
    previous = pd.DataFrame([_row("meta_ads", 0, 100, 5)])
    context = _context({"platform": "meta_ads", "account_id": "act_1", "name": "Acme"})

    payload = build_report_payload("shamuna", current, previous=previous, query_context=context)

    assert payload["deltas"]["impressions"] == 50
    assert payload["deltas"]["spend"] is None
    assert payload["summary"]["spend"] == 30
    assert payload["summary_previous"]["spend"] == 0


def test_payload_builds_daily_series_rates_and_account_scoped_narrative():
    current = pd.DataFrame([
        _row("meta_ads", 20, 100, 5, conversions=2),
        {**_row("meta_ads", 10, 50, 5, conversions=1), "date": pd.Timestamp("2026-07-02")},
    ])
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"})

    payload = build_report_payload("nutri", current, query_context=context)

    assert payload["rates"] == {
        "conversion_rate": 30.0,
        "cpa": 10.0,
        "cpc": 3.0,
        "cpm": 200.0,
        "ctr": 6.6667,
    }
    assert payload["daily_series"] == [
        {"date": "2026-07-01T00:00:00", "platform": "meta_ads", "metrics": {"clicks": 5, "conversions": 2, "impressions": 100, "spend": 20}},
        {"date": "2026-07-02T00:00:00", "platform": "meta_ads", "metrics": {"clicks": 5, "conversions": 1, "impressions": 50, "spend": 10}},
    ]
    assert payload["narratives"] == ["Acme recorded 150 impressions during 2026-07-01 to 2026-07-31."]
    assert payload["availability"]["daily_series"] is True


def test_process_api_response_preserves_exact_source_metrics_and_platform():
    source_metrics = {"spend": 5, "custom_event": 3, "nested": [{"value": "7"}]}

    frame = process_api_response(
        [{"campaign_name": "Launch", "date": "2026-07-01", "metrics": source_metrics}],
        "meta_ads",
        "client_1",
        "user_1",
    )
    source_metrics["custom_event"] = 999

    assert frame.loc[0, "source_platform"] == "meta_ads"
    assert frame.loc[0, "source_metrics"] == {
        "spend": 5,
        "custom_event": 3,
        "nested": [{"value": "7"}],
    }


@pytest.mark.parametrize("raw_metrics", [
    {"spend": "12.5", "clicks": "4"},
    {"social_spend": "12.5", "unique_clicks": "4"},
])
def test_payload_uses_normalized_canonical_values_for_numeric_string_aliases(raw_metrics):
    frame = process_api_response(
        [{
            "campaign_name": "Aliases",
            "date": "2026-07-01",
            "metrics": raw_metrics,
        }],
        "meta_ads",
        "client_1",
        "user_1",
    )
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"})
    context["required_metrics"] = ["spend", "clicks"]

    payload = build_report_payload("nutri", frame, query_context=context)

    assert payload["summary"] == {"clicks": 4, "spend": 12.5}
    assert payload["rows"]["current"][0]["source_metrics"] == raw_metrics


def test_process_api_response_protects_source_provenance_from_dynamic_fields():
    original = {"spend": 7}
    frame = process_api_response(
        [{
            "campaign_name": "Protected",
            "date": "2026-07-01",
            "metrics": original,
            "dimensions": {"source_platform": "dimension-attack", "source_metrics": {"bad": 1}},
            "source_platform": "top-level-attack",
            "source_metrics": {"bad": 2},
        }],
        "google_ads",
        "client_1",
        "user_1",
    )

    assert frame.loc[0, "source_platform"] == "google_ads"
    assert frame.loc[0, "source_metrics"] == original


def test_payload_reuses_current_and_export_before_missing_only_api(monkeypatch):
    calls = []

    def fetch(*args, **kwargs):
        calls.append((args, kwargs))
        return [{
            "campaign_name": "Supplement",
            "date": "2026-07-02",
            "metrics": {"clicks": 4, "custom_value": 9},
        }]

    monkeypatch.setattr("dashboard.reporting.fetch_campaign_data_from_api", fetch)
    current = pd.DataFrame([_row("meta_ads", 10, 100, 5)])
    current.at[0, "source_metrics"] = {"spend": 10}
    export_table = pd.DataFrame([{"campaign_name": "Launch", "impressions": 123}])
    export_table.attrs["supplied_metrics"] = {"impressions"}
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"})

    payload = build_report_payload(
        "nutri",
        current,
        export_table=export_table,
        query_context=context,
        client_id="client_1",
        user_id="user_1",
        api_key="secret",
    )

    assert calls[0][0][6] == ["clicks", "custom_value"]
    assert calls[0][1] == {"show_errors": False}
    assert payload["summary"] == {"clicks": 4, "custom_value": 9, "impressions": 123, "spend": 10}
    assert payload["rows"]["supplemental"][0]["source_metrics"] == {"clicks": 4, "custom_value": 9}
    assert payload["tables"]["export"][0]["impressions"] == 123
    assert payload["daily_series"] == [
        {"date": "2026-07-01T00:00:00", "platform": "meta_ads", "metrics": {"spend": 10}},
        {"date": "2026-07-02T00:00:00", "platform": "meta_ads", "metrics": {"clicks": 4, "custom_value": 9}},
    ]


def test_payload_does_not_augment_metrics_already_present(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("API should not be called for complete dashboard data")

    monkeypatch.setattr("dashboard.reporting.fetch_campaign_data_from_api", unexpected)
    current = pd.DataFrame([_row("meta_ads", 0, 100, 5, custom_value=0)])
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"})

    payload = build_report_payload("nutri", current, query_context=context, api_key="secret")

    assert payload["summary"] == {"clicks": 5, "custom_value": 0, "impressions": 100, "spend": 0}
    assert payload["rows"]["supplemental"] == []


def test_zero_filled_export_without_provenance_does_not_suppress_fallback(monkeypatch):
    calls = []

    def fetch(*args, **kwargs):
        calls.append(args[6])
        return [{"campaign_name": "Supplement", "date": "2026-07-02", "metrics": {"impressions": 50}}]

    monkeypatch.setattr("dashboard.reporting.fetch_campaign_data_from_api", fetch)
    current = pd.DataFrame([{**_row("meta_ads", 10, 0, 0), "source_metrics": {"spend": 10}}])
    export_table = pd.DataFrame([{"date": pd.Timestamp("2026-07-01"), "impressions": 0}])
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"})
    context["required_metrics"] = ["spend", "impressions"]

    payload = build_report_payload(
        "nutri",
        current,
        export_table=export_table,
        query_context=context,
        client_id="client_1",
        user_id="user_1",
        api_key="secret",
    )

    assert calls == [["impressions"]]
    assert payload["summary"] == {"impressions": 50, "spend": 10}
    assert payload["daily_series"][-1] == {
        "date": "2026-07-02T00:00:00",
        "platform": "meta_ads",
        "metrics": {"impressions": 50},
    }


def test_daily_series_omits_rows_without_available_metrics():
    current = pd.DataFrame([{
        "date": pd.Timestamp("2026-07-01"),
        "platform": "meta_ads",
        "source_platform": "meta_ads",
        "source_metrics": {},
        "spend": 0,
    }])
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"})
    context["required_metrics"] = ["spend"]

    payload = build_report_payload("nutri", current, query_context=context)

    assert payload["daily_series"] == []
    assert payload["availability"]["daily_series"] is False
    assert payload["availability"]["daily_series_metrics"] == {"spend": False}


def test_daily_series_includes_provenanced_export_metrics():
    export_table = pd.DataFrame([{
        "date": pd.Timestamp("2026-07-03"),
        "impressions": 25,
    }])
    export_table.attrs["supplied_metrics"] = {"impressions"}
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"})
    context["required_metrics"] = ["impressions"]

    payload = build_report_payload(
        "nutri",
        pd.DataFrame(),
        export_table=export_table,
        query_context=context,
    )

    assert payload["daily_series"] == [{
        "date": "2026-07-03T00:00:00",
        "platform": "unscoped",
        "metrics": {"impressions": 25},
    }]
    assert payload["availability"]["daily_series"] is True
    assert payload["availability"]["daily_series_metrics"] == {"impressions": True}


def test_payload_augments_missing_metrics_per_platform_without_double_counting(monkeypatch):
    calls = []

    def fetch(platform, *args, **kwargs):
        requested = args[5]
        calls.append((platform, requested))
        metrics = {"impressions": 50} if platform == "meta_ads" else {"spend": 20}
        return [{"campaign_name": "Supplement", "date": "2026-07-02", "metrics": metrics}]

    monkeypatch.setattr("dashboard.reporting.fetch_campaign_data_from_api", fetch)
    current = pd.DataFrame([
        {**_row("meta_ads", 10, 0, 0), "source_metrics": {"spend": 10}},
        {**_row("google_ads", 0, 100, 0), "source_metrics": {"impressions": 100}},
    ])
    context = _context(
        {"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"},
        {"platform": "google_ads", "account_id": "123", "account_name": "Acme"},
    )
    context["required_metrics"] = ["spend", "impressions"]

    payload = build_report_payload(
        "nutri",
        current,
        query_context=context,
        client_id="client_1",
        user_id="user_1",
        api_key="secret",
    )

    assert calls == [("meta_ads", ["impressions"]), ("google_ads", ["spend"])]
    assert payload["summary"] == {"impressions": 150, "spend": 30}
    assert payload["by_platform"] == {
        "google_ads": {"impressions": 100, "spend": 20},
        "meta_ads": {"impressions": 50, "spend": 10},
    }


def test_payload_hides_unresolved_metric_when_augmentation_fails(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("connector unavailable")

    monkeypatch.setattr("dashboard.reporting.fetch_campaign_data_from_api", fail)
    current = pd.DataFrame([_row("meta_ads", 10, 100, 5)])
    current.at[0, "source_metrics"] = {"spend": 10}
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"})

    payload = build_report_payload("nutri", current, query_context=context, api_key="secret")

    assert payload["summary"] == {"spend": 10}
    assert payload["availability"]["metrics"] == {
        "clicks": False,
        "custom_value": False,
        "impressions": False,
        "spend": True,
    }
    assert payload["availability"]["summary"] is True


def test_payload_redacts_ids_and_credentials_from_all_serialized_data():
    current = pd.DataFrame([{
        **_row("meta_ads", 10, 100, 5),
        "client_id": "client-secret-value",
        "user_id": "user-secret-value",
        "access_token": "row-access-token",
        "source_metrics": {"spend": 10, "api_key": "metric-api-key"},
    }])
    export_table = pd.DataFrame([{
        "campaign_name": "Export",
        "spend": 10,
        "user_id": "export-user",
        "password": "export-password",
    }])
    export_table.attrs["supplied_metrics"] = {"spend"}
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme"})
    context["required_metrics"].append("api_key")

    payload = build_report_payload(
        "nutri",
        current,
        export_table=export_table,
        query_context=context,
        optional={"breakdowns": {"country": [{"name": "EC", "refresh_token": "breakdown-token"}]}},
    )
    serialized = json.dumps(payload)

    for secret in (
        "client-secret-value",
        "user-secret-value",
        "row-access-token",
        "metric-api-key",
        "export-user",
        "export-password",
        "breakdown-token",
    ):
        assert secret not in serialized
    assert "client_id" not in payload["rows"]["current"][0]
    assert "user_id" not in payload["rows"]["current"][0]
    assert "password" not in payload["tables"]["export"][0]
    assert "refresh_token" not in payload["breakdowns"]["country"][0]
    assert "api_key" not in serialized


def test_safety_render_report_round_trips_hostile_text_without_executable_markup(tmp_path, monkeypatch):
    template = tmp_path / "nutri.html"
    template.write_text("<html><body><!-- REPORT_DATA --><div id='company'></div></body></html>", encoding="utf-8")
    monkeypatch.setattr(reporting, "_TEMPLATE_DIR", tmp_path)
    hostile = "Acme </script><script>alert('x')</script>&\u2028\u2029"
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": hostile})
    payload = build_report_payload("nutri", pd.DataFrame([_row("meta_ads", 1, 2, 1)]), query_context=context, api_key="top-secret")

    rendered = render_report("nutri", payload)
    serialized = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', rendered, re.S).group(1)

    assert json.loads(serialized)["meta"]["company_name"] == hostile
    assert hostile not in rendered
    assert "\\u003c/script\\u003e\\u003cscript\\u003e" in serialized
    assert "\\u0026\\u2028\\u2029" in serialized
    assert "top-secret" not in rendered
    assert rendered.count("<!-- REPORT_DATA -->") == 0
    assert rendered.count('id="report-data"') == 1
    assert ".textContent" in rendered
    assert "Number.isFinite" in rendered
    assert "innerHTML" not in rendered


def test_safety_render_report_rejects_unknown_malformed_or_reference_template(tmp_path, monkeypatch):
    monkeypatch.setattr(reporting, "_TEMPLATE_DIR", tmp_path)
    (tmp_path / "nutri.html").write_text("<html>missing marker</html>", encoding="utf-8")

    with pytest.raises(ValueError, match="^Unknown report template: unknown$"):
        render_report("unknown", {})

    with pytest.raises(ValueError, match="^Report template must contain exactly one data marker$"):
        render_report("nutri", {})

    (tmp_path / "nutri.html").write_text("<html>Shamuna confidential<!-- REPORT_DATA --></html>", encoding="utf-8")
    with pytest.raises(ValueError, match="^Report template contains reference-client content$"):
        render_report("nutri", {})


def test_safety_asset_url_requires_https_and_an_allowlisted_host():
    allowed = {"media.example.com"}

    assert safe_asset_url("https://media.example.com/chart.png", allowed) == "https://media.example.com/chart.png"
    assert safe_asset_url("http://media.example.com/chart.png", allowed) is None
    assert safe_asset_url("https://evil.example/chart.png", allowed) is None
    assert safe_asset_url("https://media.example.com.evil.test/chart.png", allowed) is None
    assert safe_asset_url("javascript:alert(1)", allowed) is None


def test_safety_render_report_rejects_paths_and_assets_outside_allowlists(tmp_path, monkeypatch):
    templates = tmp_path / "templates"
    templates.mkdir()
    outside = tmp_path / "outside.html"
    outside.write_text("<html><!-- REPORT_DATA --></html>", encoding="utf-8")
    monkeypatch.setattr(reporting, "_TEMPLATE_DIR", templates)
    monkeypatch.setitem(reporting._TEMPLATE_FILES, "nutri", "../outside.html")

    with pytest.raises(ValueError, match="^Report template path is outside the allowlisted directory$"):
        render_report("nutri", {})

    monkeypatch.setitem(reporting._TEMPLATE_FILES, "nutri", "nutri.html")
    (templates / "nutri.html").write_text(
        '<html><img src="https://reference.example/logo.png"><!-- REPORT_DATA --></html>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="^Report template contains an unsafe asset URL$"):
        render_report("nutri", {})

    (templates / "nutri.html").write_text(
        '<html><img src="javascript:alert(1)"><!-- REPORT_DATA --></html>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="^Report template contains an unsafe asset URL$"):
        render_report("nutri", {})


def _complete_template_payload():
    return {
        "meta": {
            "company_name": "Acme Foods",
            "accounts": [{"account_id": "act_1", "name": "Acme Foods", "platform": "meta_ads"}],
            "platforms": ["meta_ads", "google_ads"],
            "filters": {"campaign": ["Launch"]},
            "period": {"start": "2026-07-01", "end": "2026-07-31"},
            "previous_period": {"start": "2026-06-01", "end": "2026-06-30"},
            "generated_at": "2026-08-17T12:00:00+00:00",
        },
        "summary": {"spend": 1500, "impressions": 250000, "reach": 180000, "clicks": 5000, "conversions": 320},
        "summary_previous": {"spend": 1400, "impressions": 225000, "reach": 170000, "clicks": 4500, "conversions": 280},
        "rates": {"ctr": 2, "cpc": 0.3, "cpm": 6, "cpa": 4.6875, "conversion_rate": 6.4},
        "deltas": {"spend": 7.1429, "impressions": 11.1111, "reach": 5.8824, "clicks": 11.1111, "conversions": 14.2857},
        "by_platform": {
            "meta_ads": {"spend": 900, "impressions": 150000, "reach": 110000, "clicks": 3200},
            "google_ads": {"spend": 600, "impressions": 100000, "reach": 70000, "clicks": 1800},
        },
        "daily_series": [
            {"date": "2026-07-01T00:00:00", "platform": "meta_ads", "metrics": {"spend": 400, "impressions": 70000, "clicks": 1400}},
            {"date": "2026-07-02T00:00:00", "platform": "meta_ads", "metrics": {"spend": 500, "impressions": 80000, "clicks": 1800}},
            {"date": "2026-07-02T00:00:00", "platform": "google_ads", "metrics": {"spend": 600, "impressions": 100000, "clicks": 1800}},
        ],
        "rows": {
            "current": [
                {"campaign_name": "Launch video", "date": "2026-07-02", "source_platform": "meta_ads", "source_metrics": {"spend": 500, "impressions": 80000, "reach": 60000, "clicks": 1800}},
                {"campaign_name": "Search launch", "date": "2026-07-02", "source_platform": "google_ads", "source_metrics": {"spend": 600, "impressions": 100000, "clicks": 1800, "conversions": 180}},
            ],
            "prior": [],
            "supplemental": [],
        },
        "breakdowns": {
            "age": [{"label": "25–34", "value": 45}, {"label": "35–44", "value": 30}],
            "gender": [{"label": "Women", "value": 62}, {"label": "Men", "value": 38}],
            "country": [{"label": "Ecuador", "value": 125000}],
            "city": [{"label": "Quito", "value": 70000}, {"label": "Guayaquil", "value": 55000}],
        },
        "tables": {"export": [{"campaign_name": "Launch video", "spend": 500, "impressions": 80000}]},
        "narratives": ["Acme Foods recorded 250000 impressions during 2026-07-01 to 2026-07-31."],
        "availability": {
            "summary": True,
            "daily_series": True,
            "breakdowns": True,
            "export_table": True,
            "narratives": True,
        },
    }


def _adriana_builder_payload():
    rows = []
    for day in range(1, 32):
        rows.append({
            "campaign_name": f"City campaign {day}",
            "date": f"2026-07-{day:02d}",
            "dimensions": {"city": "Quito" if day % 2 else "Guayaquil", "country": "Ecuador"},
            "metrics": {
                "spend": str(day),
                "impressions": str(day * 1000),
                "reach": str(day * 800),
                "clicks": str(day * 10),
                "lead": str(day),
            },
        })
    frames = [process_api_response(rows, "meta_ads", "client_1", "user_1")]
    frames.append(process_api_response([{
        "campaign_name": "Product collection pin",
        "date": "2026-07-15",
        "dimensions": {"country": "United States", "product_name": "Product Alpha"},
        "metrics": {"spend": "125.5", "impressions": "18000", "clicks": "420", "outbound_clicks": "205", "saves": "31"},
    }], "pinterest_ads", "client_1", "user_1"))
    frames.append(process_api_response([{
        "campaign_name": "Search traffic",
        "date": "2026-07-16",
        "dimensions": {"country": "United States"},
        "metrics": {"spend": "240", "impressions": "22000", "clicks": "510", "conversions": "24"},
    }], "google_ads", "client_1", "user_1"))
    frames.append(process_api_response([{
        "campaign_name": "Product Alpha traffic",
        "date": "2026-07-17",
        "dimensions": {"country": "United States", "product_name": "Product Alpha"},
        "metrics": {"sessions": "380", "users": "290", "pageviews": "640"},
    }], "google_analytics", "client_1", "user_1"))
    context = _context(
        {"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme Design"},
        {"platform": "pinterest_ads", "account_id": "pin_1", "account_name": "Acme Design"},
        {"platform": "google_ads", "account_id": "ads_1", "account_name": "Acme Design"},
        {"platform": "google_analytics", "account_id": "ga_1", "account_name": "Acme Design"},
    )
    context["required_metrics"] = [
        "spend", "impressions", "reach", "clicks", "lead", "conversions",
        "outbound_clicks", "saves", "sessions", "users", "pageviews",
    ]
    return build_report_payload(
        "adriana_hoyos",
        pd.concat(frames, ignore_index=True),
        query_context=context,
        optional={"breakdowns": {
            "campaign": [{"label": "City campaign", "value": 496000}, {"label": "Product collection pin", "value": 18000}],
        }},
    )


def _artz_builder_payload(with_publishers=True):
    meta_rows = []
    for day in range(1, 32):
        item = {
            "campaign_name": f"Meta daily {day}",
            "date": f"2026-07-{day:02d}",
            "metrics": {
                "social_spend": "1",
                "impressions": str(day * 100),
                "reach": str(day * 80),
                "total_interactions": str(day * 2),
                "unique_clicks": "1",
            },
        }
        if with_publishers:
            item["dimensions"] = {"publisher_platform": "facebook"}
        meta_rows.append(item)
    if with_publishers:
        meta_rows.append({
            "campaign_name": "Instagram launch",
            "date": "2026-07-15",
            "dimensions": {"publisher_platform": "instagram"},
            "metrics": {
                "social_spend": 20.5,
                "impressions": 2000,
                "reach": 1500,
                "total_interactions": 100,
                "unique_clicks": 2.5,
                "lead": 3,
            },
        })
    frames = [process_api_response(meta_rows, "meta_ads", "client_1", "user_1")]
    frames.append(process_api_response([{
        "campaign_name": "TikTok awareness",
        "date": "2026-07-16",
        "metrics": {
            "cost": "30",
            "views": "5000",
            "reach": "4000",
            "total_interactions": "250",
            "unique_clicks": "75",
        },
    }], "tiktok_ads", "client_1", "user_1"))
    frames.append(process_api_response([{
        "campaign_name": "Google search",
        "date": "2026-07-17",
        "metrics": {
            "cost": 40,
            "impressions": 6000,
            "unique_clicks": 120.5,
            "actions": 8,
        },
    }], "google_ads", "client_1", "user_1"))
    context = _context(
        {"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme Center"},
        {"platform": "tiktok_ads", "account_id": "tt_1", "account_name": "Acme Center"},
        {"platform": "google_ads", "account_id": "ga_1", "account_name": "Acme Center"},
    )
    context["required_metrics"] = [
        "spend", "impressions", "reach", "engagement", "clicks", "conversions", "views",
    ]
    return build_report_payload(
        "artz",
        pd.concat(frames, ignore_index=True),
        query_context=context,
        optional={"breakdowns": {
            "competition": [
                {"label": "Market Alpha", "followers": 7200, "engagement": 3.4},
                {"label": "Market Beta", "followers": 6800, "engagement": 2.8},
            ],
            "facebook": {"age": [{"label": "25–34", "value": 45}]},
            "instagram": {"gender": [{"label": "Women", "value": 62}]},
            "tiktok": {"age": [{"label": "18–24", "value": 51}]},
        }},
    )


def _shamuna_builder_payload(with_publishers=True):
    meta_rows = []
    for day in range(1, 32):
        item = {
            "campaign_name": f"Meta daily {day}",
            "date": f"2026-07-{day:02d}",
            "metrics": {
                "social_spend": "1",
                "impressions": str(day * 100),
                "reach": str(day * 80),
                "total_interactions": str(day * 2),
                "unique_clicks": "1",
            },
        }
        if with_publishers:
            item["dimensions"] = {"publisher_platform": "facebook"}
        meta_rows.append(item)
    if with_publishers:
        meta_rows.append({
            "campaign_name": "Instagram launch",
            "date": "2026-07-15",
            "dimensions": {"publisher_platform": "instagram"},
            "metrics": {
                "social_spend": 20.5,
                "impressions": 2000,
                "reach": 1500,
                "total_interactions": 100,
                "unique_clicks": 2.5,
                "lead": 3,
            },
        })
    frames = [process_api_response(meta_rows, "meta_ads", "client_1", "user_1")]
    frames.append(process_api_response([{
        "campaign_name": "TikTok awareness",
        "date": "2026-07-16",
        "metrics": {
            "cost": "30",
            "impressions": "5000",
            "reach": "4000",
            "total_interactions": "250",
            "unique_clicks": "75",
        },
    }], "tiktok_ads", "client_1", "user_1"))
    frames.append(process_api_response([{
        "campaign_name": "Search campaigns",
        "date": "2026-07-17",
        "metrics": {
            "cost": 40,
            "impressions": 6000,
            "unique_clicks": 120.5,
            "actions": 8,
        },
    }], "google_ads", "client_1", "user_1"))
    context = _context(
        {"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme Shamuna"},
        {"platform": "tiktok_ads", "account_id": "tt_1", "account_name": "Acme Shamuna"},
        {"platform": "google_ads", "account_id": "ga_1", "account_name": "Acme Shamuna"},
    )
    context["required_metrics"] = [
        "spend", "impressions", "reach", "engagement", "clicks", "conversions", "views",
    ]
    return build_report_payload(
        "shamuna",
        pd.concat(frames, ignore_index=True),
        query_context=context,
        optional={"breakdowns": {
            "competition": [
                {"label": "Market Alpha", "followers": 7200, "engagement": 3.4},
                {"label": "Market Beta", "followers": 6800, "engagement": 2.8},
            ],
            "facebook": {"age": [{"label": "25–34", "value": 45}]},
            "instagram": {"gender": [{"label": "Women", "value": 62}]},
            "tiktok": {"age": [{"label": "18–24", "value": 51}]},
        }},
    )


def _nutri_payload():
    payload = _complete_template_payload()
    payload["meta"]["platforms"] = ["facebook", "instagram", "tiktok"]
    payload["summary"].update({"engagement": 14000, "followers": 8500, "views": 420000})
    payload["by_platform"] = {
        "facebook": {"spend": 650, "impressions": 110000, "reach": 90000, "engagement": 6200, "followers": 4000, "views": 180000},
        "instagram": {"spend": 550, "impressions": 90000, "reach": 65000, "engagement": 5100, "followers": 3000, "views": 140000},
        "tiktok": {"spend": 300, "impressions": 50000, "reach": 25000, "engagement": 2700, "followers": 1500, "views": 100000},
    }
    payload["daily_series"] = [
        {
            "date": f"2026-07-{day:02d}T00:00:00",
            "platform": platform,
            "metrics": {"impressions": day * factor, "spend": day * factor / 100},
        }
        for day in range(1, 32)
        for platform, factor in (("facebook", 1000), ("instagram", 800), ("tiktok", 500))
    ]
    payload["rows"]["current"] = [
        {"campaign_name": "Community story", "source_platform": "facebook", "source_metrics": {"impressions": 50000, "engagement": 3500}},
        {"campaign_name": "Product reel", "source_platform": "instagram", "source_metrics": {"impressions": 42000, "engagement": 2800}},
        {"campaign_name": "Short recipe", "source_platform": "tiktok", "source_metrics": {"views": 65000, "engagement": 1900}},
    ]
    payload["breakdowns"] = {
        "competition": [
            {"label": "Market Alpha", "followers": 7200, "engagement": 3.4},
            {"label": "Market Beta", "followers": 6800, "engagement": 2.8},
        ],
        "facebook": {"age": [{"label": "25–34", "value": 45}], "country": [{"label": "Ecuador", "value": 90}]},
        "instagram": {"gender": [{"label": "Women", "value": 62}], "city": [{"label": "Quito", "value": 55}]},
        "tiktok": {"age": [{"label": "18–24", "value": 51}], "region": [{"label": "Pichincha", "value": 44}]},
    }
    payload["narratives"] = [
        "Acme Foods recorded measurable multichannel results in the selected period.",
        {"platform": "facebook", "text": "Acme Foods Facebook activity was led by Community story."},
        {"platform": "instagram", "text": "Acme Foods Instagram activity was led by Product reel."},
        {"platform": "tiktok", "text": "Acme Foods TikTok activity was led by Short recipe."},
    ]
    return payload


def _meta_builder_payload(
    with_publishers,
    publisher_values=None,
    campaign_suffixes=None,
    numeric_strings=False,
    numeric_aliases=False,
):
    publishers = publisher_values or (
        ("facebook", "facebook", "instagram", "instagram") if with_publishers else (None,) * 4
    )
    raw_rows = []
    suffixes = campaign_suffixes or (None,) * 4
    for index, (day, publisher, spend, impressions, reach, engagement, views) in enumerate((
        (1, publishers[0], 10, 1000, 800, 100, 500),
        (2, publishers[1], 20, 2000, 1500, 200, 600),
        (1, publishers[2], 30, 3000, 2200, 300, 700),
        (2, publishers[3], 40, 4000, 3000, 400, 800),
    )):
        suffix = f"_{suffixes[index]}" if suffixes[index] else ""
        metrics = {
            "spend": spend,
            "impressions": impressions,
            "reach": reach,
            "engagement": engagement,
            "views": views,
        }
        if numeric_strings:
            metrics = {
                "social_spend": str(spend),
                "impressions": str(impressions),
                "reach": str(reach),
                "total_interactions": str(engagement),
                "unique_clicks": str(spend // 10),
            }
        elif numeric_aliases:
            metrics = {
                "social_spend": spend,
                "impressions": impressions,
                "reach": reach,
                "total_interactions": engagement,
                "unique_clicks": spend // 10 + 0.5,
                "lead": day,
            }
        item = {
            "campaign_name": f"Meta launch {day}-{spend}{suffix}",
            "date": f"2026-07-{day:02d}",
            "metrics": metrics,
        }
        if publisher:
            item["dimensions"] = {"publisher_platform": publisher}
        raw_rows.append(item)
    frame = process_api_response(raw_rows, "meta_ads", "client_1", "user_1")
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme Foods"})
    context["required_metrics"] = ["spend", "impressions", "reach", "engagement", "views"]
    if numeric_strings or numeric_aliases:
        context["required_metrics"].append("clicks")
    if numeric_aliases:
        context["required_metrics"].append("conversions")
    optional = {
        "breakdowns": {
            "facebook": {"age": [{"label": "25–34", "value": 45}]},
            "instagram": {"age": [{"label": "25–34", "value": 40}]},
        }
    } if with_publishers and not (numeric_strings or numeric_aliases) else None
    return build_report_payload("nutri", frame, query_context=context, optional=optional)


class _BrowserResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.recording = False
        self.value = []

    def handle_starttag(self, tag, attrs):
        if dict(attrs).get("id") == "browser-result":
            self.recording = True

    def handle_endtag(self, tag):
        if self.recording and tag == "script":
            self.recording = False

    def handle_data(self, data):
        if self.recording:
            self.value.append(data)


def _browser_dom(rendered, tmp_path, custom_probe=None, filename="nutri-browser.html"):
    browser = (
        shutil.which("google-chrome")
        or shutil.which("chromium")
        or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    )
    assert Path(browser).is_file(), "A real Chrome/Chromium executable is required for report DOM tests"
    instrumentation = r"""
<script>
window.__browserErrors = [];
window.__browserConsoleErrors = [];
window.addEventListener("error", event => window.__browserErrors.push(event.message));
window.addEventListener("unhandledrejection", event => window.__browserErrors.push(String(event.reason)));
const originalConsoleError = console.error.bind(console);
console.error = (...args) => {
  window.__browserConsoleErrors.push(args.map(String).join(" "));
  originalConsoleError(...args);
};
</script>
"""
    probe = custom_probe or r"""
<script>
(() => {
  document.body.classList.add("show-all-panels");
  const panelIds = ["summary-panel", "competition-panel", "facebook-panel", "instagram-panel", "tiktok-panel", "investment-panel"];
  const visible = id => {
    const node = document.getElementById(id);
    return Boolean(node && !node.hidden && getComputedStyle(node).display !== "none");
  };
  const rgb = value => (value.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
  const luminance = value => {
    const parts = rgb(value).map(channel => {
      const normalized = channel / 255;
      return normalized <= .03928 ? normalized / 12.92 : ((normalized + .055) / 1.055) ** 2.4;
    });
    return .2126 * parts[0] + .7152 * parts[1] + .0722 * parts[2];
  };
  const contrast = node => {
    const foreground = luminance(getComputedStyle(node).color);
    const background = luminance(getComputedStyle(document.body).backgroundColor);
    return (Math.max(foreground, background) + .05) / (Math.min(foreground, background) + .05);
  };
  const count = selector => document.querySelectorAll(selector).length;
  const familyCount = (panel, family) => [...document.querySelectorAll(`#${panel} [data-family="${family}"]`)].filter(node => !node.hidden && node.getClientRects().length).length;
  const trendCharts = [...document.querySelectorAll('[data-family="trend-chart"]:not([hidden])')];
  const result = {
    company: document.getElementById("company-name")?.textContent,
    period: document.getElementById("report-period")?.textContent,
    visible: Object.fromEntries(panelIds.map(id => [id, visible(id)])),
    summary: {
      kpis: familyCount("summary-panel", "kpi"), charts: familyCount("summary-panel", "trend-chart"),
      tables: familyCount("summary-panel", "table"), narratives: familyCount("summary-panel", "narrative")
    },
    competitionRows: count("#competition-body tr"),
    platforms: Object.fromEntries(["facebook", "instagram", "tiktok"].map(name => [name, {
      kpis: familyCount(`${name}-panel`, "kpi"), charts: familyCount(`${name}-panel`, "trend-chart"),
      tables: familyCount(`${name}-panel`, "table"), content: familyCount(`${name}-panel`, "content"),
      demographics: familyCount(`${name}-panel`, "demographics"), narratives: familyCount(`${name}-panel`, "narrative")
    }])),
    investment: {tables: familyCount("investment-panel", "table"), optimization: familyCount("investment-panel", "optimization")},
    summaryKpis: Object.fromEntries([...document.querySelectorAll('#summary-panel [data-metric]')].map(card => [card.dataset.metric, card.querySelector('.stat-value')?.textContent])),
    platformKpis: Object.fromEntries(["facebook", "instagram", "tiktok"].map(name => [name, Object.fromEntries([...document.querySelectorAll(`#${name}-panel [data-metric]`)].map(card => [card.dataset.metric, card.querySelector('.stat-value')?.textContent]))])),
    platformTrendRows: Object.fromEntries(["facebook", "instagram", "tiktok"].map(name => [name, [...document.querySelectorAll(`#${name}-trend-body tr td:last-child`)].map(cell => cell.textContent)])),
    platformContentRows: Object.fromEntries(["facebook", "instagram", "tiktok"].map(name => [name, [...document.querySelectorAll(`#${name}-content-body tr td:first-child`)].map(cell => cell.textContent)])),
    sharedNotices: Object.fromEntries(["facebook", "instagram"].map(name => [name, document.getElementById(`${name}-shared-meta`)?.textContent || ""])),
    investmentRows: [...document.querySelectorAll("#investment-body tr")].map(row => row.textContent),
    maxTrendTicks: Math.max(0, ...trendCharts.map(chart => chart.querySelectorAll("[data-trend-tick]").length)),
    minTrendRows: Math.min(...[...document.querySelectorAll('[data-family="trend-table"]:not([hidden])')].map(table => table.querySelectorAll("tbody tr").length)),
    minAccentContrast: Math.min(...[...document.querySelectorAll(".accent-text")].map(contrast)),
    errors: [...window.__browserErrors, ...window.__browserConsoleErrors],
    resources: performance.getEntriesByType("resource").map(entry => entry.name),
    text: document.body.textContent
  };
  const output = document.createElement("script");
  output.id = "browser-result";
  output.type = "application/json";
  output.textContent = JSON.stringify(result);
  document.body.append(output);
})();
</script>
"""
    report_path = tmp_path / filename
    report_path.write_text(
        rendered.replace("<head>", "<head>" + instrumentation).replace("</body>", probe + "</body>"),
        encoding="utf-8",
    )
    process = subprocess.Popen(
        [
            browser, "--headless=new", "--disable-gpu", "--no-sandbox",
            f"--user-data-dir={tmp_path / 'chrome-profile'}", "--virtual-time-budget=1000",
            "--dump-dom", report_path.as_uri(),
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
    parser = _BrowserResultParser()
    parser.feed(stdout)
    assert parser.value, stderr
    return json.loads("".join(parser.value))


def test_nutri_browser_preserves_reference_panels_and_dynamic_content(tmp_path):
    dom = _browser_dom(render_report("nutri", _nutri_payload()), tmp_path)

    assert dom["company"] == "Acme Foods"
    assert dom["period"] == "01 jul 2026 — 31 jul 2026"
    assert dom["visible"] == {panel: True for panel in dom["visible"]}
    assert dom["summary"] == {"kpis": 6, "charts": 0, "tables": 1, "narratives": 1}
    assert dom["competitionRows"] == 2
    for platform in ("facebook", "instagram", "tiktok"):
        assert dom["platforms"][platform] == {
            "kpis": 6, "charts": 0 if platform == "facebook" else 1, "tables": 0 if platform == "facebook" else 1, "content": 1, "demographics": 1, "narratives": 1,
        }
    assert dom["investment"] == {"tables": 1, "optimization": 1}
    assert dom["maxTrendTicks"] <= 7
    assert dom["minTrendRows"] == 31
    assert dom["minAccentContrast"] >= 4.5


def test_nutri_browser_rankings_use_delivery_period_even_for_older_posts(tmp_path):
    def post(name, reach, publisher="facebook", **extra):
        return {
            "name": name,
            "source_platform": "meta_ads",
            "publisher_platform": publisher,
            "source_metrics": {
                "spend": 1,
                "impressions": reach,
                "reach": reach,
                "engagement": reach,
            },
            **extra,
        }

    payload = {
        "meta": {"company_name": "Acme", "platforms": ["meta_ads"], "period": {"start": "2026-08-01", "end": "2026-08-31"}},
        "summary": {}, "summary_previous": {}, "rates": {}, "deltas": {}, "by_platform": {},
        "daily_series": [],
        "rows": {"current": [
            post("Evergreen old post", 1000, post_message="Evergreen old post", created_time="2026-07-31T23:59:59+0000", url="https://www.facebook.com/acme/posts/old"),
            post("PROMOCIÓN DICIEMBRE 2025", 900, post_message="PROMOCIÓN DICIEMBRE 2025", url="https://www.facebook.com/acme/posts/december"),
            post("Agosto actual", 30, post_message="Texto real de agosto", post_created_time="2026-08-12T10:30:00+0000", url="https://www.facebook.com/acme/posts/august"),
            post("CAMPAÑA AGOSTO 2026", 20, post_title="Contenido de agosto"),
            post("Internal row", 10, ad_name="AD NAME", campaign_name="CAMPAIGN NAME", post_created_time="2026-08-15T10:30:00+0000"),
            post("Instagram actual", 2000, publisher="instagram", post_title="Instagram actual", post_created_time="2026-08-14T10:30:00+0000", url="https://www.instagram.com/p/ig-1/"),
        ], "prior": [], "supplemental": []},
        "breakdowns": {}, "tables": {"export": []}, "narratives": [], "availability": {},
    }
    probe = r"""
<script>
(() => {
  const output = document.createElement("script");
  output.id = "browser-result";
  output.type = "application/json";
  output.textContent = JSON.stringify({
    reachPosts: [...document.querySelectorAll("#facebook-top-reach-grid .post-caption")].map(node => node.textContent),
    spend: document.querySelector('#facebook-kpis [data-metric="spend"] .stat-value')?.textContent,
    iframeCount: document.querySelectorAll("#facebook-top-reach-grid iframe").length,
    errors: [...window.__browserErrors, ...window.__browserConsoleErrors],
  });
  document.body.append(output);
})();
</script>
"""

    dom = _browser_dom(render_report("nutri", payload), tmp_path, probe, "nutri-period-posts.html")

    assert dom == {
        "reachPosts": ["Evergreen old post", "PROMOCIÓN DICIEMBRE 2025", "Texto real de agosto"],
        "spend": "$5,00",
        "iframeCount": 3,
        "errors": [],
    }


def test_nutri_ad_rankings_are_not_filtered_by_post_publication_date():
    source = (Path(__file__).parents[1] / "dashboard/report_templates/nutri/script.js").read_text(encoding="utf-8")

    assert "const rankingContentRows = Array.isArray(rows.content) && rows.content.length ? rows.content : metricRows;" in source
    assert "const contentInPeriod" not in source


def test_nutri_template_has_lead_ranking_containers_before_reach():
    rendered = render_report("nutri", {})
    element_ids = set(re.findall(r'\bid="([^"]+)"', rendered))

    assert {
        "facebook-top-lead-card",
        "facebook-top-lead-grid",
        "instagram-posts-content",
        "instagram-top-lead-card",
        "instagram-top-lead-grid",
        "instagram-top-reach-card",
        "instagram-top-reach-grid",
        "instagram-top-engagement-card",
        "instagram-top-engagement-grid",
        "instagram-lowest-card",
        "instagram-lowest-grid",
    } <= element_ids
    for network in ("facebook", "instagram"):
        lead_index = rendered.index(f'id="{network}-top-lead-card"')
        reach_index = rendered.index(f'id="{network}-top-reach-card"')
        assert lead_index < reach_index
        assert rendered[lead_index:reach_index].count("<article") == 1


def test_nutri_browser_renders_separate_top_three_meta_rankings_with_embeds(tmp_path):
    def post(network, rank, reach, engagement):
        slug = f"{network}-{rank}"
        url = (
            f"https://www.facebook.com/acme/posts/{slug}"
            if network == "facebook"
            else f"https://www.instagram.com/p/{slug}/"
        )
        body = (
            ""
            if network == "facebook"
            else f'<iframe src="https://www.instagram.com/p/{slug}/embed/captioned/"></iframe>'
        )
        return {
            "name": f"{network.title()} post {rank}",
            "post_message": f"{network.title()} post {rank}",
            "source_platform": "meta_ads",
            "publisher_platform": network,
            "url": url,
            "body": body,
            "source_metrics": {
                "impressions": reach,
                "reach": reach,
                "engagement": engagement,
                "views": reach,
            },
        }

    payload = {
        "meta": {
            "company_name": "Acme",
            "platforms": ["meta_ads"],
            "period": {"start": "2026-08-01", "end": "2026-08-31"},
        },
        "summary": {},
        "summary_previous": {},
        "rates": {},
        "deltas": {},
        "by_platform": {},
        "daily_series": [],
        "rows": {
            "current": [
                post("facebook", 1, 900, 10),
                post("instagram", 1, 800, 11),
                post("facebook", 2, 700, 20),
                post("instagram", 2, 600, 21),
                post("facebook", 3, 500, 30),
                post("instagram", 3, 400, 31),
                post("facebook", 4, 100, 40),
                post("instagram", 4, 200, 41),
            ],
            "prior": [],
            "supplemental": [],
        },
        "breakdowns": {},
        "tables": {"export": []},
        "narratives": [],
        "availability": {},
    }
    probe = r"""
<script>
(() => {
  const ranking = network => ({
    reach: [...document.querySelectorAll(`#${network}-top-reach-grid .post-caption`)].map(node => node.textContent),
    engagement: [...document.querySelectorAll(`#${network}-top-engagement-grid .post-caption`)].map(node => node.textContent),
    iframeSources: [...document.querySelectorAll(`#${network}-top-reach-grid iframe`)].map(node => node.src),
  });
  const output = document.createElement("script");
  output.id = "browser-result";
  output.type = "application/json";
  output.textContent = JSON.stringify({
    facebook: ranking("facebook"),
    instagram: ranking("instagram"),
    errors: [...window.__browserErrors, ...window.__browserConsoleErrors],
  });
  document.body.append(output);
})();
</script>
"""

    dom = _browser_dom(render_report("nutri", payload), tmp_path, probe, "nutri-network-rankings.html")

    assert dom["facebook"]["reach"] == ["Facebook post 1", "Facebook post 2", "Facebook post 3"]
    assert dom["instagram"]["reach"] == ["Instagram post 1", "Instagram post 2", "Instagram post 3"]
    assert dom["facebook"]["engagement"] == ["Facebook post 4", "Facebook post 3", "Facebook post 2"]
    assert dom["instagram"]["engagement"] == ["Instagram post 4", "Instagram post 3", "Instagram post 2"]
    assert len(dom["facebook"]["iframeSources"]) == 3
    assert len(dom["instagram"]["iframeSources"]) == 3
    assert all("facebook.com/plugins/post.php" in url for url in dom["facebook"]["iframeSources"])
    assert all("instagram.com/" in url for url in dom["instagram"]["iframeSources"])
    assert dom["errors"] == []


def test_nutri_browser_lead_rankings_are_independent_stable_and_lead_first(tmp_path):
    def post(network, name, reach, source_lead=None, top_lead=None):
        slug = name.lower().replace(" ", "-")
        url = (
            f"https://www.facebook.com/acme/posts/{slug}"
            if network == "facebook"
            else f"https://www.instagram.com/p/{slug}/"
        )
        metrics = {"impressions": reach, "reach": reach, "engagement": reach}
        if source_lead is not None:
            metrics["lead"] = source_lead
        item = {
            "post_message": name,
            "source_platform": "meta_ads",
            "publisher_platform": network,
            "url": url,
            "source_metrics": metrics,
        }
        if top_lead is not None:
            item["lead"] = top_lead
        return item

    payload = {
        "meta": {"company_name": "Acme", "platforms": ["meta_ads"], "period": {}},
        "summary": {}, "summary_previous": {}, "rates": {}, "deltas": {}, "by_platform": {},
        "daily_series": [],
        "rows": {"current": [
            post("facebook", "Facebook missing", 900),
            post("facebook", "Facebook source", 800, source_lead=7, top_lead=99),
            post("facebook", "Facebook invalid", 700, source_lead="11", top_lead="8"),
            post("facebook", "Facebook fallback", 600, top_lead=9),
            post("instagram", "Instagram zero one", 400, source_lead=0),
            post("instagram", "Instagram missing", 300),
            post("instagram", "Instagram invalid", 200, source_lead="5"),
            post("instagram", "Instagram zero four", 100, top_lead=0),
        ], "prior": [], "supplemental": []},
        "breakdowns": {}, "tables": {"export": []}, "narratives": [], "availability": {},
    }
    probe = r"""
<script>
(() => {
  const ranking = network => ({
    lead: [...document.querySelectorAll(`#${network}-top-lead-grid .post-caption`)].map(node => node.textContent),
    firstKpis: [...document.querySelectorAll(`#${network}-top-lead-grid .post-card`)].map(card => card.querySelector(".kpi-row span")?.textContent),
    leadValues: [...document.querySelectorAll(`#${network}-top-lead-grid .post-card`)].map(card => card.querySelector(".kpi-row strong")?.textContent),
    iframeSources: [...document.querySelectorAll(`#${network}-top-lead-grid iframe`)].map(node => node.src),
    links: [...document.querySelectorAll(`#${network}-top-lead-grid .kpi-row:last-child a`)].map(node => node.href),
    reach: [...document.querySelectorAll(`#${network}-top-reach-grid .post-caption`)].map(node => node.textContent),
  });
  const output = document.createElement("script");
  output.id = "browser-result";
  output.type = "application/json";
  output.textContent = JSON.stringify({
    facebook: ranking("facebook"),
    instagram: ranking("instagram"),
    errors: [...window.__browserErrors, ...window.__browserConsoleErrors],
  });
  document.body.append(output);
})();
</script>
"""

    dom = _browser_dom(render_report("nutri", payload), tmp_path, probe, "nutri-lead-rankings.html")

    assert dom["facebook"]["lead"] == ["Facebook fallback", "Facebook source", "Facebook missing"]
    assert dom["facebook"]["leadValues"] == ["9", "7", "0"]
    assert dom["facebook"]["reach"] == ["Facebook missing", "Facebook source", "Facebook invalid"]
    assert dom["instagram"]["lead"] == ["Instagram zero one", "Instagram missing", "Instagram invalid"]
    assert dom["instagram"]["leadValues"] == ["0", "0", "0"]
    for network in ("facebook", "instagram"):
        assert dom[network]["firstKpis"] == ["Clientes potenciales"] * 3
        assert len(dom[network]["iframeSources"]) == 3
        assert all(network + ".com" in url for url in dom[network]["iframeSources"])
        assert len(dom[network]["links"]) == 3
        assert all(dom[network]["links"])
        for caption, url in zip(dom[network]["lead"], dom[network]["links"], strict=True):
            slug = caption.lower().replace(" ", "-")
            expected = (
                f"https://www.facebook.com/acme/posts/{slug}"
                if network == "facebook"
                else f"https://www.instagram.com/p/{slug}/"
            )
            assert url == expected
    assert dom["errors"] == []

    empty_payload = {**payload, "rows": {"current": [], "prior": [], "supplemental": []}}
    empty_probe = r"""
<script>
(() => {
  const output = document.createElement("script");
  output.id = "browser-result";
  output.type = "application/json";
  output.textContent = JSON.stringify(Object.fromEntries(["facebook", "instagram"].map(network => [network, {
    hidden: document.getElementById(`${network}-top-lead-card`).hidden,
    cards: document.querySelectorAll(`#${network}-top-lead-grid .post-card`).length,
  }])));
  document.body.append(output);
})();
</script>
"""
    empty_dom = _browser_dom(render_report("nutri", empty_payload), tmp_path, empty_probe, "nutri-empty-lead-rankings.html")
    assert empty_dom == {
        "facebook": {"hidden": True, "cards": 0},
        "instagram": {"hidden": True, "cards": 0},
    }


def test_nutri_facebook_embed_uses_facebook_plugin_in_downloaded_html():
    source = (Path(__file__).parents[1] / "dashboard/report_templates/nutri/script.js").read_text(encoding="utf-8")

    assert 'contentPlatform === "facebook" && directPostUrl.startsWith("http") && directPostUrl.includes("facebook.com")' in source
    assert "isFacebookPreviewUrl(item.iframe_url)" in source
    assert "if (supportedEmbed)" in source
    assert '!window.location.protocol.startsWith("file")' not in source
    assert 'contentPlatform === "facebook" && !isFacebookPreviewUrl(iframeEmbedUrl)' in source
    assert "const isPublicPostUrl" in source
    assert ".some(isPublicPostUrl)" in source
    assert 'item.name !== "Publicación" ? item.name : "Publicación " + (item.platform === "facebook" ? "Facebook" : "Instagram")' in source
    assert 'const postTitle = postCopy || item.post_name || item.content_name || "Publicación"' in source


def test_nutri_facebook_preview_prefers_meta_ad_preview_for_dynamic_posts():
    source = (Path(__file__).parents[1] / "dashboard/report_templates/nutri/script.js").read_text(encoding="utf-8")

    assert "const isFacebookPreviewUrl" in source
    assert "business.facebook.com/ads/api/preview_iframe.php" in source
    assert "isFacebookPreviewUrl(iframeEmbedUrl)" in source


def test_nutri_browser_hides_empty_panels_and_does_not_show_investment_for_summary_spend(tmp_path):
    payload = {
        "meta": {"company_name": "Acme", "platforms": [], "period": {"start": "2026-07-01", "end": "2026-07-31"}},
        "summary": {"spend": 25}, "summary_previous": {}, "rates": {}, "deltas": {}, "by_platform": {},
        "daily_series": [], "rows": {"current": [], "prior": [], "supplemental": []},
        "breakdowns": {}, "tables": {"export": []}, "narratives": [], "availability": {},
    }

    dom = _browser_dom(render_report("nutri", payload), tmp_path)

    assert dom["company"] == "Acme"
    assert dom["period"] == "01 jul 2026 — 31 jul 2026"
    assert dom["visible"] == {
        "summary-panel": True,
        "competition-panel": False,
        "facebook-panel": False,
        "instagram-panel": False,
        "tiktok-panel": False,
        "investment-panel": False,
    }
    assert "Datos no disponibles" not in dom["text"]


def test_nutri_browser_hides_missing_subsections_inside_an_available_platform(tmp_path):
    payload = {
        "meta": {"company_name": "Acme", "platforms": ["facebook"], "period": {"start": "2026-07-01", "end": "2026-07-31"}},
        "summary": {}, "summary_previous": {}, "rates": {}, "deltas": {},
        "by_platform": {"facebook": {"spend": 25}}, "daily_series": [],
        "rows": {"current": [], "prior": [], "supplemental": []},
        "breakdowns": {}, "tables": {"export": []}, "narratives": [], "availability": {},
    }

    dom = _browser_dom(render_report("nutri", payload), tmp_path)

    assert dom["visible"] == {
        "summary-panel": True,
        "competition-panel": False,
        "facebook-panel": True,
        "instagram-panel": False,
        "tiktok-panel": False,
        "investment-panel": True,
    }
    assert dom["platforms"]["facebook"] == {
        "kpis": 1, "charts": 0, "tables": 0, "content": 0, "demographics": 0, "narratives": 0,
    }


def test_nutri_browser_maps_builder_meta_publishers_without_double_counting(tmp_path):
    payload = _meta_builder_payload(with_publishers=True)

    assert payload["meta"]["platforms"] == ["meta_ads"]
    assert {row["source_platform"] for row in payload["rows"]["current"]} == {"meta_ads"}

    dom = _browser_dom(render_report("nutri", payload), tmp_path)

    assert dom["visible"]["facebook-panel"] is True
    assert dom["visible"]["instagram-panel"] is True
    assert dom["visible"]["tiktok-panel"] is False
    assert dom["platformKpis"]["facebook"]["spend"] == "$30,00"
    assert dom["platformKpis"]["instagram"]["spend"] == "$70,00"
    assert dom["platformTrendRows"]["facebook"] == []
    assert dom["platformTrendRows"]["instagram"] == ["3.000", "4.000"]
    assert dom["platformContentRows"]["facebook"] == ["Meta launch 2-20", "Meta launch 1-10"]
    assert dom["platformContentRows"]["instagram"] == ["Meta launch 2-40", "Meta launch 1-30"]
    assert dom["summaryKpis"]["spend"] == "$100,00"
    assert dom["sharedNotices"] == {"facebook": "", "instagram": ""}
    assert len(dom["investmentRows"]) == 1
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_nutri_browser_normalizes_numeric_string_meta_publisher_metrics(tmp_path):
    payload = _meta_builder_payload(with_publishers=True, numeric_strings=True)

    assert all(
        isinstance(row["source_metrics"]["social_spend"], str)
        for row in payload["rows"]["current"]
    )
    assert payload["by_platform"]["meta_ads"] == {
        "clicks": 10,
        "engagement": 1000,
        "impressions": 10000,
        "reach": 7500,
        "spend": 100,
    }

    dom = _browser_dom(render_report("nutri", payload), tmp_path)

    assert dom["visible"]["facebook-panel"] is True
    assert dom["visible"]["instagram-panel"] is True
    assert dom["platformKpis"]["facebook"] == {
        "spend": "$30,00",
        "impressions": "3.000",
        "reach": "2.300",
        "engagement": "300",
        "clicks": "3",
    }
    assert dom["platformKpis"]["instagram"] == {
        "spend": "$70,00",
        "impressions": "7.000",
        "reach": "5.200",
        "engagement": "700",
        "clicks": "7",
    }
    assert dom["platformTrendRows"]["facebook"] == []
    assert dom["platformTrendRows"]["instagram"] == ["3.000", "4.000"]
    assert dom["platformContentRows"]["facebook"] == ["Meta launch 2-20", "Meta launch 1-10"]
    assert dom["platformContentRows"]["instagram"] == ["Meta launch 2-40", "Meta launch 1-30"]
    assert dom["summaryKpis"]["spend"] == "$100,00"
    assert len(dom["investmentRows"]) == 1
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_nutri_browser_prefers_finite_numeric_aliases_over_normalized_rows(tmp_path):
    payload = _meta_builder_payload(with_publishers=True, numeric_aliases=True)

    assert payload["rows"]["current"][0]["source_metrics"]["unique_clicks"] == 1.5
    assert payload["rows"]["current"][0]["clicks"] == 1
    assert payload["by_platform"]["meta_ads"]["conversions"] == 6

    dom = _browser_dom(render_report("nutri", payload), tmp_path)

    assert dom["platformKpis"]["facebook"] == {
        "spend": "$30,00",
        "impressions": "3.000",
        "reach": "2.300",
        "engagement": "300",
        "clicks": "4",
        "conversions": "3",
    }
    assert dom["platformKpis"]["instagram"] == {
        "spend": "$70,00",
        "impressions": "7.000",
        "reach": "5.200",
        "engagement": "700",
        "clicks": "8",
        "conversions": "3",
    }
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_nutri_browser_shares_unsplit_meta_aggregate_without_inventing_channel_split(tmp_path):
    payload = _meta_builder_payload(with_publishers=False)

    assert payload["meta"]["platforms"] == ["meta_ads"]
    assert {row["platform"] for row in payload["rows"]["current"]} == {"meta_ads"}

    dom = _browser_dom(render_report("nutri", payload), tmp_path)

    assert dom["visible"]["facebook-panel"] is True
    assert dom["visible"]["instagram-panel"] is True
    assert dom["platformKpis"]["facebook"] == dom["platformKpis"]["instagram"]
    assert dom["platformKpis"]["facebook"]["spend"] == "$100,00"
    assert dom["sharedNotices"] == {
        "facebook": "Datos agregados de Meta compartidos entre Facebook e Instagram; no se atribuye una distribución por red.",
        "instagram": "Datos agregados de Meta compartidos entre Facebook e Instagram; no se atribuye una distribución por red.",
    }
    assert dom["platforms"]["facebook"]["content"] == 0
    assert dom["platforms"]["instagram"]["content"] == 0
    assert len(dom["investmentRows"]) == 1
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_nutri_browser_does_not_share_meta_when_another_publisher_is_identified(tmp_path):
    payload = _meta_builder_payload(
        with_publishers=False,
        publisher_values=("audience_network",) * 4,
    )

    assert {row["publisher_platform"] for row in payload["rows"]["current"]} == {"audience_network"}

    dom = _browser_dom(render_report("nutri", payload), tmp_path)

    assert dom["visible"]["facebook-panel"] is False
    assert dom["visible"]["instagram-panel"] is False
    assert dom["sharedNotices"] == {"facebook": "", "instagram": ""}
    assert len(dom["investmentRows"]) == 1
    assert dom["errors"] == []


def test_nutri_browser_maps_inferred_meta_publishers_without_shared_fallback(tmp_path):
    payload = _meta_builder_payload(
        with_publishers=False,
        campaign_suffixes=("facebook", "facebook", "instagram", "instagram"),
    )

    assert all("publisher_platform" not in row for row in payload["rows"]["current"])
    assert {row["platform"] for row in payload["rows"]["current"]} == {"Facebook Ads", "Instagram Ads"}

    dom = _browser_dom(render_report("nutri", payload), tmp_path)

    assert dom["platformKpis"]["facebook"]["spend"] == "$30,00"
    assert dom["platformKpis"]["instagram"]["spend"] == "$70,00"
    assert dom["platformContentRows"]["facebook"] == ["Meta launch 2-20_facebook", "Meta launch 1-10_facebook"]
    assert dom["platformContentRows"]["instagram"] == ["Meta launch 2-40_instagram", "Meta launch 1-30_instagram"]
    assert dom["sharedNotices"] == {"facebook": "", "instagram": ""}
    assert dom["errors"] == []


def test_nutri_browser_keeps_direct_channel_content_despite_conflicting_nested_publisher(tmp_path):
    payload = _nutri_payload()
    payload["rows"]["current"][0]["source_metrics"]["publisher_platform"] = "instagram"

    dom = _browser_dom(render_report("nutri", payload), tmp_path)

    assert "Community story" in dom["platformContentRows"]["facebook"]
    assert "Community story" not in dom["platformContentRows"]["instagram"]
    assert dom["errors"] == []


def test_nutri_browser_harness_captures_console_errors(tmp_path):
    rendered = render_report("nutri", _nutri_payload()).replace(
        "</body>", '<script>console.error("console probe")</script></body>',
    )

    dom = _browser_dom(rendered, tmp_path)

    assert dom["errors"] == ["console probe"]


def test_nutri_template_has_no_reference_assets_requests_or_authoring_controls():
    rendered = render_report("nutri", _nutri_payload())

    for forbidden in (
        "innerHTML", "contenteditable", "downloadHTML", "downloadPDF", "openPin", "<img", "<iframe",
        "http://", "https://", "fetch(", "XMLHttpRequest", "WebSocket", "window.open",
    ):
        assert forbidden not in rendered
    for leaked_identity in (
        "parmalat", "la lechera", "toni", "vita", "shamuna", "adriana hoyos", "artz",
        "dra. gaby", "la toña", "yogurt fresa", "cumbayá",
    ):
        assert leaked_identity not in rendered.casefold()


_ADRIANA_BROWSER_PROBE = r"""
<script>
(() => {
  const visible = id => {
    const node = document.getElementById(id);
    return Boolean(node && !node.hidden && getComputedStyle(node).display !== "none");
  };
  const countVisible = selector => [...document.querySelectorAll(selector)].filter(node => !node.hidden && node.getClientRects().length).length;
  const rgb = value => (value.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
  const luminance = value => {
    const parts = rgb(value).map(channel => {
      const normalized = channel / 255;
      return normalized <= .03928 ? normalized / 12.92 : ((normalized + .055) / 1.055) ** 2.4;
    });
    return .2126 * parts[0] + .7152 * parts[1] + .0722 * parts[2];
  };
  const contrast = node => {
    const foreground = luminance(getComputedStyle(node).color);
    const background = luminance(getComputedStyle(document.body).backgroundColor);
    return (Math.max(foreground, background) + .05) / (Math.min(foreground, background) + .05);
  };
  const sectionIds = ["season-report", "summer-report", "ao2-report", "insights-report"];
  const accents = [...document.querySelectorAll(".accent-text")];
  const result = {
    company: document.getElementById("company-name")?.textContent,
    period: document.getElementById("report-period")?.textContent,
    visible: Object.fromEntries(sectionIds.map(id => [id, visible(id)])),
    season: {
      funnel: countVisible("#season-funnel [data-stage]"),
      cities: countVisible("#season-city-body tr"),
      campaigns: countVisible("#season-campaign-body tr"),
    },
    summer: {
      kpis: countVisible("#summer-kpis [data-metric]"),
      charts: countVisible('#summer-report [data-family="daily-chart"]'),
      daily: countVisible("#summer-daily-body tr"),
      campaigns: countVisible("#summer-campaign-body tr"),
    },
    ao2: {
      channels: countVisible("#ao2-channels [data-platform]"),
      pinterest: countVisible("#pinterest-body tr"),
      products: countVisible("#product-body tr"),
      traffic: countVisible("#traffic-body tr"),
      countries: countVisible("#country-body tr"),
      charts: countVisible('#ao2-report [data-family="traffic-chart"]'),
    },
    insights: [...document.querySelectorAll("#insights-list .narrative")].map(node => node.textContent),
    cityValues: Object.fromEntries([...document.querySelectorAll("#season-city-body tr")].map(row => [row.cells[0].textContent, row.cells[1].textContent])),
    countryValues: Object.fromEntries([...document.querySelectorAll("#country-body tr")].map(row => [row.cells[0].textContent, row.cells[1].textContent])),
    maxTrendTicks: Math.max(0, ...[...document.querySelectorAll('[data-family="daily-chart"]')].map(chart => chart.querySelectorAll("[data-trend-tick]").length)),
    minAccentContrast: accents.length ? Math.min(...accents.map(contrast)) : null,
    errors: [...window.__browserErrors, ...window.__browserConsoleErrors],
    resources: performance.getEntriesByType("resource").map(entry => entry.name),
    text: document.body.textContent,
  };
  const output = document.createElement("script");
  output.id = "browser-result";
  output.type = "application/json";
  output.textContent = JSON.stringify(result);
  document.body.append(output);
})();
</script>
"""


def test_adriana_hoyos_browser_preserves_distinct_reports_with_real_builder_data(tmp_path):
    payload = _adriana_builder_payload()

    assert payload["meta"]["platforms"] == ["meta_ads", "pinterest_ads", "google_ads", "google_analytics"]
    assert isinstance(payload["rows"]["current"][0]["source_metrics"]["spend"], str)

    dom = _browser_dom(
        render_report("adriana_hoyos", payload),
        tmp_path,
        _ADRIANA_BROWSER_PROBE,
        "adriana-browser.html",
    )

    assert dom["company"] == "Acme Design"
    assert dom["period"] == "01 jul 2026 — 31 jul 2026"
    assert dom["visible"] == {section: True for section in dom["visible"]}
    assert dom["season"] == {"funnel": 5, "cities": 2, "campaigns": 2}
    assert dom["summer"]["kpis"] >= 8
    assert dom["summer"]["charts"] == 1
    assert dom["summer"]["daily"] == 33
    assert dom["summer"]["campaigns"] == 12
    assert dom["ao2"] == {
        "channels": 3,
        "pinterest": 1,
        "products": 1,
        "traffic": 3,
        "countries": 2,
        "charts": 1,
    }
    assert dom["cityValues"] == {"Quito": "256.000", "Guayaquil": "240.000"}
    assert dom["countryValues"] == {"Ecuador": "496.000", "United States": "40.000"}
    assert dom["insights"] == ["Acme Design recorded 536000 impressions during 2026-07-01 to 2026-07-31."]
    assert dom["maxTrendTicks"] <= 7
    assert dom["minAccentContrast"] >= 4.5
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_adriana_hoyos_browser_hides_every_unavailable_report_from_real_builder_payload(tmp_path):
    context = _context({"platform": "meta_ads", "account_id": "act_2", "account_name": "Acme Empty"})
    payload = build_report_payload("adriana_hoyos", pd.DataFrame(), query_context=context)

    dom = _browser_dom(
        render_report("adriana_hoyos", payload),
        tmp_path,
        _ADRIANA_BROWSER_PROBE,
        "adriana-empty-browser.html",
    )

    assert dom["company"] == "Acme Empty"
    assert dom["period"] == "01 jul 2026 — 31 jul 2026"
    assert dom["visible"] == {section: False for section in dom["visible"]}
    assert dom["season"] == {"funnel": 0, "cities": 0, "campaigns": 0}
    assert dom["summer"] == {"kpis": 0, "charts": 0, "daily": 0, "campaigns": 0}
    assert dom["ao2"] == {"channels": 0, "pinterest": 0, "products": 0, "traffic": 0, "countries": 0, "charts": 0}
    assert dom["insights"] == []
    assert "Datos no disponibles" not in dom["text"]
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_adriana_hoyos_browser_hides_missing_subsections_in_partial_builder_payload(tmp_path):
    frame = process_api_response([{
        "campaign_name": "Discovery campaign",
        "date": "2026-07-20",
        "dimensions": {"country": "United States"},
        "metrics": {"spend": "40", "impressions": "5000", "clicks": "125"},
    }], "pinterest_ads", "client_1", "user_1")
    context = _context({"platform": "pinterest_ads", "account_id": "pin_2", "account_name": "Acme Partial"})
    context["required_metrics"] = ["spend", "impressions", "clicks"]
    payload = build_report_payload("adriana_hoyos", frame, query_context=context)

    dom = _browser_dom(
        render_report("adriana_hoyos", payload),
        tmp_path,
        _ADRIANA_BROWSER_PROBE,
        "adriana-partial-browser.html",
    )

    assert dom["visible"] == {section: True for section in dom["visible"]}
    assert dom["season"] == {"funnel": 2, "cities": 0, "campaigns": 1}
    assert dom["summer"] == {"kpis": 6, "charts": 1, "daily": 1, "campaigns": 1}
    assert dom["ao2"] == {"channels": 1, "pinterest": 1, "products": 0, "traffic": 1, "countries": 1, "charts": 1}
    assert dom["cityValues"] == {}
    assert dom["countryValues"] == {"United States": "5.000"}
    assert "Datos no disponibles" not in dom["text"]
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_adriana_hoyos_template_has_no_reference_facts_assets_requests_or_controls():
    rendered = render_report("adriana_hoyos", _adriana_builder_payload())

    for forbidden in (
        "innerHTML", "contenteditable", "downloadHTML", "downloadPDF", "openPin", "<img", "<video", "<iframe",
        "http://", "https://", "fetch(", "XMLHttpRequest", "WebSocket", "window.open",
    ):
        assert forbidden not in rendered
    for leaked_identity in (
        "parmalat", "la lechera", "toni", "vita", "nutri", "shamuna", "adriana hoyos", "artz",
        "season refresh", "summer sale", "galápagos iconic", "miami", "florida",
    ):
        assert leaked_identity not in rendered.casefold()


def test_adriana_hoyos_browser_resolves_row_aliases_and_string_metrics(tmp_path):
    rows = []
    for day in range(1, 4):
        rows.append({
            "campaign_name": f"Aliased Meta Campaign {day}",
            "date": f"2026-07-0{day}",
            "dimensions": {"city": "Quito", "country": "Ecuador"},
            "metrics": {
                "social_spend": str(day * 10),
                "impressions": str(day * 1000),
                "unique_clicks": str(day * 5),
                "lead": str(day),
            },
        })
    frame = process_api_response(rows, "meta_ads", "client_1", "user_1")
    context = _context({"platform": "meta_ads", "account_id": "act_alias", "account_name": "Acme Alias"})
    context["required_metrics"] = ["spend", "impressions", "clicks", "lead"]
    payload = build_report_payload("adriana_hoyos", frame, query_context=context)

    dom = _browser_dom(
        render_report("adriana_hoyos", payload),
        tmp_path,
        _ADRIANA_BROWSER_PROBE,
        "adriana-alias-browser.html",
    )

    assert dom["season"]["campaigns"] == 3
    assert dom["summer"]["campaigns"] == 3
    assert dom["errors"] == []



_ARTZ_BROWSER_PROBE = r"""
<script>
(() => {
  const panelIds = ["summary-panel", "competition-panel", "facebook-panel", "instagram-panel", "tiktok-panel", "google-panel", "investment-panel"];
  const platformNames = ["facebook", "instagram", "tiktok", "google"];
  const visible = id => {
    const node = document.getElementById(id);
    return Boolean(node && !node.hidden && getComputedStyle(node).display !== "none");
  };
  const kpis = name => Object.fromEntries([...document.querySelectorAll(`#${name}-kpis [data-metric]`)].map(card => [card.dataset.metric, card.querySelector(".stat-value")?.textContent]));
  const result = {
    company: document.getElementById("company-name")?.textContent,
    period: document.getElementById("report-period")?.textContent,
    visible: Object.fromEntries(panelIds.map(id => [id, visible(id)])),
    platformKpis: Object.fromEntries(platformNames.map(name => [name, kpis(name)])),
    trendRows: Object.fromEntries(platformNames.map(name => [name, document.querySelectorAll(`#${name}-trend-body tr`).length])),
    trendTicks: Object.fromEntries(platformNames.map(name => [name, document.querySelectorAll(`#${name}-chart [data-trend-tick]`).length])),
    trendTitles: Object.fromEntries(platformNames.map(name => [name, [...document.querySelectorAll(`#${name}-chart title`)].map(node => node.textContent)])),
    contentRows: Object.fromEntries(platformNames.map(name => [name, [...document.querySelectorAll(`#${name}-content-body tr td:first-child`)].map(cell => cell.textContent)])),
    sharedNotices: Object.fromEntries(["facebook", "instagram"].map(name => [name, document.getElementById(`${name}-shared-meta`)?.textContent || ""])),
    competitionRows: document.querySelectorAll("#competition-body tr").length,
    investmentRows: document.querySelectorAll("#investment-body tr").length,
    optimizationItems: document.querySelectorAll("#optimization-list .breakdown-meta").length,
    errors: [...window.__browserErrors, ...window.__browserConsoleErrors],
    resources: performance.getEntriesByType("resource").map(entry => entry.name),
    text: document.body.textContent,
  };
  const output = document.createElement("script");
  output.id = "browser-result";
  output.type = "application/json";
  output.textContent = JSON.stringify(result);
  document.body.append(output);
})();
</script>
"""


def test_artz_browser_restores_reference_hierarchy_with_builder_numeric_metrics(tmp_path):
    payload = _artz_builder_payload()

    facebook = next(row for row in payload["rows"]["current"] if row["platform"] == "Facebook Ads")
    instagram = next(row for row in payload["rows"]["current"] if row["platform"] == "Instagram Ads")
    assert isinstance(facebook["source_metrics"]["social_spend"], str)
    assert facebook["spend"] == 1
    assert instagram["source_metrics"]["unique_clicks"] == 2.5
    assert instagram["clicks"] == 2

    dom = _browser_dom(
        render_report("artz", payload),
        tmp_path,
        _ARTZ_BROWSER_PROBE,
        "artz-browser.html",
    )

    assert dom["company"] == "Acme Center"
    assert dom["period"] == "01 jul 2026 — 31 jul 2026"
    assert dom["visible"] == {panel: True for panel in dom["visible"]}
    assert dom["competitionRows"] == 2
    assert dom["platformKpis"]["facebook"] == {
        "spend": "$31,00",
        "impressions": "49.600",
        "reach": "39.680",
        "engagement": "992",
        "clicks": "31",
    }
    assert dom["platformKpis"]["instagram"] == {
        "spend": "$20,50",
        "impressions": "2.000",
        "reach": "1.500",
        "engagement": "100",
        "clicks": "2,5",
        "conversions": "3",
    }
    assert dom["platformKpis"]["tiktok"] == {
        "spend": "$30,00",
        "impressions": "5.000",
        "reach": "4.000",
        "engagement": "250",
        "clicks": "75",
    }
    assert dom["platformKpis"]["google"] == {
        "spend": "$40,00",
        "impressions": "6.000",
        "clicks": "120,5",
        "conversions": "8",
    }
    assert dom["trendRows"]["facebook"] == 31
    assert dom["trendTicks"]["facebook"] <= 7
    assert len(dom["trendTitles"]["facebook"]) == 31
    assert dom["trendTitles"]["facebook"][-1] == "31 jul 2026: 3.100"
    assert dom["investmentRows"] == 3
    assert dom["optimizationItems"] > 0
    assert dom["sharedNotices"] == {"facebook": "", "instagram": ""}
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_artz_browser_labels_unsplit_meta_as_shared_without_attributing_content(tmp_path):
    payload = _artz_builder_payload(with_publishers=False)

    assert all(row["platform"] == "meta_ads" for row in payload["rows"]["current"] if row["source_platform"] == "meta_ads")

    dom = _browser_dom(
        render_report("artz", payload),
        tmp_path,
        _ARTZ_BROWSER_PROBE,
        "artz-unsplit-browser.html",
    )

    notice = "Datos agregados de Meta compartidos entre Facebook e Instagram; no se atribuye una distribución por red."
    assert dom["visible"]["facebook-panel"] is True
    assert dom["visible"]["instagram-panel"] is True
    assert dom["platformKpis"]["facebook"] == dom["platformKpis"]["instagram"]
    assert dom["platformKpis"]["facebook"]["spend"] == "$31,00"
    assert dom["sharedNotices"] == {"facebook": notice, "instagram": notice}
    assert dom["contentRows"]["facebook"] == []
    assert dom["contentRows"]["instagram"] == []
    assert dom["investmentRows"] == 3
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_artz_browser_hides_every_unavailable_panel_from_real_builder_payload(tmp_path):
    context = _context({"platform": "meta_ads", "account_id": "act_2", "account_name": "Acme Empty"})
    payload = build_report_payload("artz", pd.DataFrame(), query_context=context)

    dom = _browser_dom(
        render_report("artz", payload),
        tmp_path,
        _ARTZ_BROWSER_PROBE,
        "artz-empty-browser.html",
    )

    assert dom["company"] == "Acme Empty"
    assert dom["period"] == "01 jul 2026 — 31 jul 2026"
    assert dom["visible"] == {panel: False for panel in dom["visible"]}
    assert dom["competitionRows"] == 0
    assert dom["investmentRows"] == 0
    assert "Datos no disponibles" not in dom["text"]
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_artz_template_has_no_reference_facts_assets_requests_or_controls():
    rendered = render_report("artz", _artz_builder_payload())

    for forbidden in (
        "innerHTML", "contenteditable", "downloadHTML", "downloadPDF", "openPin", "<img", "<video", "<iframe",
        "src=", "href=", "http://", "https://", "fetch(", "XMLHttpRequest", "WebSocket", "window.open",
        "updateEmbed", "../ARTZ_files", "assets ARTZ",
    ):
        assert forbidden not in rendered
    for leaked_identity in (
        "parmalat", "la lechera", "toni", "vita", "nutri", "shamuna", "adriana hoyos", "artz",
        "dra. gaby", "la toña", "yogurt fresa", "cumbayá", "feed normal", "modo agencia",
    ):
        assert leaked_identity not in rendered.casefold()


_SHAMUNA_BROWSER_PROBE = r"""
<script>
(() => {
  const panelIds = ["summary-panel", "competition-panel", "facebook-panel", "instagram-panel", "tiktok-panel", "google-panel", "investment-panel"];
  const visible = id => {
    const node = document.getElementById(id);
    return Boolean(node && !node.hidden && getComputedStyle(node).display !== "none");
  };
  const panelKpis = prefix => Object.fromEntries(
    [...document.querySelectorAll(`#${prefix}-kpis [data-metric]`)].map(card => [
      card.dataset.metric,
      card.querySelector(".stat-value")?.textContent?.trim(),
    ])
  );
  const result = {
    company: document.getElementById("company-name")?.textContent,
    period: document.getElementById("report-period")?.textContent,
    visible: Object.fromEntries(panelIds.map(id => [id, visible(id)])),
    competitionRows: document.querySelectorAll("#competition-body tr").length,
    platformKpis: {
      facebook: panelKpis("facebook"),
      instagram: panelKpis("instagram"),
      tiktok: panelKpis("tiktok"),
      google: panelKpis("google"),
    },
    trendRows: {
      facebook: document.querySelectorAll("#facebook-trend-body tr").length,
      instagram: document.querySelectorAll("#instagram-trend-body tr").length,
      tiktok: document.querySelectorAll("#tiktok-trend-body tr").length,
      google: document.querySelectorAll("#google-trend-body tr").length,
    },
    trendTicks: {
      facebook: document.querySelectorAll("#facebook-chart [data-trend-tick]").length,
    },
    trendTitles: {
      facebook: [...document.querySelectorAll("#facebook-chart .chart-dot title")].map(node => node.textContent),
    },
    contentRows: {
      facebook: [...document.querySelectorAll("#facebook-content-body tr")].map(row => row.cells[0]?.textContent),
      instagram: [...document.querySelectorAll("#instagram-content-body tr")].map(row => row.cells[0]?.textContent),
    },
    investmentRows: document.querySelectorAll("#investment-body tr").length,
    optimizationItems: document.querySelectorAll("#optimization-list .breakdown-meta").length,
    sharedNotices: {
      facebook: document.getElementById("facebook-shared-meta")?.textContent || "",
      instagram: document.getElementById("instagram-shared-meta")?.textContent || "",
    },
    errors: [...window.__browserErrors, ...window.__browserConsoleErrors],
    resources: performance.getEntriesByType("resource").map(entry => entry.name),
    text: document.body.textContent,
  };
  const output = document.createElement("script");
  output.id = "browser-result";
  output.type = "application/json";
  output.textContent = JSON.stringify(result);
  document.body.append(output);
})();
</script>
"""


def test_shamuna_browser_restores_reference_hierarchy_with_builder_numeric_metrics(tmp_path):
    payload = _shamuna_builder_payload()

    facebook = next(row for row in payload["rows"]["current"] if row["platform"] == "Facebook Ads")
    instagram = next(row for row in payload["rows"]["current"] if row["platform"] == "Instagram Ads")
    assert isinstance(facebook["source_metrics"]["social_spend"], str)
    assert facebook["spend"] == 1
    assert instagram["source_metrics"]["unique_clicks"] == 2.5
    assert instagram["clicks"] == 2

    dom = _browser_dom(
        render_report("shamuna", payload),
        tmp_path,
        _SHAMUNA_BROWSER_PROBE,
        "shamuna-browser.html",
    )

    assert dom["company"] == "Acme Shamuna"
    assert dom["period"] == "01 jul 2026 — 31 jul 2026"
    assert dom["visible"] == {panel: True for panel in dom["visible"]}
    assert dom["competitionRows"] == 2
    assert dom["platformKpis"]["facebook"] == {
        "spend": "$31,00",
        "impressions": "49.600",
        "reach": "39.680",
        "engagement": "992",
        "clicks": "31",
    }
    assert dom["platformKpis"]["instagram"] == {
        "spend": "$20,50",
        "impressions": "2.000",
        "reach": "1.500",
        "engagement": "100",
        "clicks": "2,5",
        "conversions": "3",
    }
    assert dom["platformKpis"]["tiktok"] == {
        "spend": "$30,00",
        "impressions": "5.000",
        "reach": "4.000",
        "engagement": "250",
        "clicks": "75",
    }
    assert dom["platformKpis"]["google"] == {
        "spend": "$40,00",
        "impressions": "6.000",
        "clicks": "120,5",
        "conversions": "8",
    }
    assert dom["trendRows"]["facebook"] == 31
    assert dom["trendTicks"]["facebook"] <= 7
    assert len(dom["trendTitles"]["facebook"]) == 31
    assert dom["trendTitles"]["facebook"][-1] == "31 jul 2026: 3.100"
    assert dom["investmentRows"] == 3
    assert dom["optimizationItems"] > 0
    assert dom["sharedNotices"] == {"facebook": "", "instagram": ""}
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_shamuna_browser_labels_unsplit_meta_as_shared_without_attributing_content(tmp_path):
    payload = _shamuna_builder_payload(with_publishers=False)

    assert all(row["platform"] == "meta_ads" for row in payload["rows"]["current"] if row["source_platform"] == "meta_ads")

    dom = _browser_dom(
        render_report("shamuna", payload),
        tmp_path,
        _SHAMUNA_BROWSER_PROBE,
        "shamuna-unsplit-browser.html",
    )

    notice = "Datos agregados de Meta compartidos entre Facebook e Instagram; no se atribuye una distribución por red."
    assert dom["visible"]["facebook-panel"] is True
    assert dom["visible"]["instagram-panel"] is True
    assert dom["platformKpis"]["facebook"] == dom["platformKpis"]["instagram"]
    assert dom["platformKpis"]["facebook"]["spend"] == "$31,00"
    assert dom["sharedNotices"] == {"facebook": notice, "instagram": notice}
    assert dom["contentRows"]["facebook"] == []
    assert dom["contentRows"]["instagram"] == []
    assert dom["investmentRows"] == 3
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_shamuna_browser_hides_every_unavailable_panel_from_real_builder_payload(tmp_path):
    context = _context({"platform": "meta_ads", "account_id": "act_2", "account_name": "Acme Empty"})
    payload = build_report_payload("shamuna", pd.DataFrame(), query_context=context)

    dom = _browser_dom(
        render_report("shamuna", payload),
        tmp_path,
        _SHAMUNA_BROWSER_PROBE,
        "shamuna-empty-browser.html",
    )

    assert dom["company"] == "Acme Empty"
    assert dom["period"] == "01 jul 2026 — 31 jul 2026"
    assert dom["visible"] == {panel: False for panel in dom["visible"]}
    assert dom["competitionRows"] == 0
    assert dom["investmentRows"] == 0
    assert "Datos no disponibles" not in dom["text"]
    assert dom["errors"] == []
    assert dom["resources"] == []


def test_shamuna_template_has_no_reference_facts_assets_requests_or_controls():
    rendered = render_report("shamuna", _shamuna_builder_payload())

    for forbidden in (
        "innerHTML", "contenteditable", "downloadHTML", "downloadPDF", "openPin", "<img", "<video", "<iframe",
        "src=", "href=", "http://", "https://", "fetch(", "XMLHttpRequest", "WebSocket", "window.open",
        "updateEmbed", "../Shamuna_files", "assets Shamuna",
    ):
        assert forbidden not in rendered
    for leaked_identity in (
        "parmalat", "la lechera", "toni", "vita", "nutri", "adriana hoyos", "artz",
        "dra. gaby", "la toña", "yogurt fresa", "cumbayá", "feed normal", "modo agencia",
    ):
        assert leaked_identity not in rendered.casefold()
