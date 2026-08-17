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


def _meta_builder_payload(with_publishers, publisher_values=None, campaign_suffixes=None):
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
        item = {
            "campaign_name": f"Meta launch {day}-{spend}{suffix}",
            "date": f"2026-07-{day:02d}",
            "metrics": {
                "spend": spend,
                "impressions": impressions,
                "reach": reach,
                "engagement": engagement,
                "views": views,
            },
        }
        if publisher:
            item["dimensions"] = {"publisher_platform": publisher}
        raw_rows.append(item)
    frame = process_api_response(raw_rows, "meta_ads", "client_1", "user_1")
    context = _context({"platform": "meta_ads", "account_id": "act_1", "account_name": "Acme Foods"})
    context["required_metrics"] = ["spend", "impressions", "reach", "engagement", "views"]
    optional = {
        "breakdowns": {
            "facebook": {"age": [{"label": "25–34", "value": 45}]},
            "instagram": {"age": [{"label": "25–34", "value": 40}]},
        }
    } if with_publishers else None
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


def _browser_dom(rendered, tmp_path):
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
    probe = r"""
<script>
(() => {
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
    report_path = tmp_path / "nutri-browser.html"
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
    assert dom["summary"] == {"kpis": 8, "charts": 1, "tables": 1, "narratives": 1}
    assert dom["competitionRows"] == 2
    for platform in ("facebook", "instagram", "tiktok"):
        assert dom["platforms"][platform] == {
            "kpis": 6, "charts": 1, "tables": 1, "content": 1, "demographics": 1, "narratives": 1,
        }
    assert dom["investment"] == {"tables": 1, "optimization": 1}
    assert dom["maxTrendTicks"] <= 7
    assert dom["minTrendRows"] == 31
    assert dom["minAccentContrast"] >= 4.5


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
    assert dom["platformTrendRows"]["facebook"] == ["1.000", "2.000"]
    assert dom["platformTrendRows"]["instagram"] == ["3.000", "4.000"]
    assert dom["platformContentRows"]["facebook"] == ["Meta launch 2-20", "Meta launch 1-10"]
    assert dom["platformContentRows"]["instagram"] == ["Meta launch 2-40", "Meta launch 1-30"]
    assert dom["summaryKpis"]["spend"] == "$100,00"
    assert dom["sharedNotices"] == {"facebook": "", "instagram": ""}
    assert len(dom["investmentRows"]) == 1
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


def test_adriana_hoyos_template_is_a_complete_payload_driven_report():
    rendered = render_report("adriana_hoyos", _complete_template_payload())

    for section_id in (
        "cover-section",
        "overview-section",
        "funnel-section",
        "channels-section",
        "trend-section",
        "campaigns-section",
        "geography-section",
        "content-section",
        "insights-section",
    ):
        assert f'id="{section_id}"' in rendered
    assert rendered.count('data-report-section="true"') == 8
    assert "Acme Foods" in rendered
    assert "2026-07-01" in rendered
    assert 'timeZone: "UTC"' in rendered
    assert "Embudo de resultados" in rendered
    assert "Rendimiento por canal" in rendered
    assert "Detalle de campañas" in rendered
    assert "Análisis geográfico" in rendered
    assert "window.REPORT_DATA" in rendered
    assert ".textContent" in rendered
    assert "Number.isFinite" in rendered


def test_adriana_hoyos_template_hides_unavailable_sections_and_has_no_reference_leaks():
    rendered = render_report("adriana_hoyos", {
        "meta": {"company_name": "Acme", "platforms": [], "period": {"start": "2026-07-01", "end": "2026-07-31"}},
        "summary": {}, "rates": {}, "deltas": {}, "by_platform": {}, "daily_series": [],
        "rows": {"current": [], "prior": [], "supplemental": []},
        "breakdowns": {}, "tables": {"export": []}, "narratives": [], "availability": {},
    })

    assert rendered.count('data-report-section="true" hidden') == 8
    assert 'showSection("geography-section", geographyRows.length > 0)' in rendered
    assert 'showSection("insights-section", narratives.length > 0)' in rendered
    assert "Datos no disponibles" not in rendered
    assert "innerHTML" not in rendered
    assert "contenteditable" not in rendered
    assert "downloadHTML" not in rendered
    assert "downloadPDF" not in rendered
    assert "openPin" not in rendered
    assert "<img" not in rendered
    assert "http://" not in rendered and "https://" not in rendered
    for leaked_identity in (
        "parmalat", "la lechera", "toni", "vita", "nutri", "shamuna", "adriana hoyos", "artz",
        "season refresh", "summer sale", "galápagos iconic",
    ):
        assert leaked_identity not in rendered.casefold()


def test_artz_template_is_a_complete_payload_driven_report():
    rendered = render_report("artz", _complete_template_payload())

    for section_id in (
        "cover-section",
        "overview-section",
        "budget-section",
        "channels-section",
        "trend-section",
        "campaigns-section",
        "audience-section",
        "creative-section",
        "insights-section",
    ):
        assert f'id="{section_id}"' in rendered
    assert rendered.count('data-report-section="true"') == 8
    assert "Acme Foods" in rendered
    assert "2026-07-01" in rendered
    assert 'timeZone: "UTC"' in rendered
    assert "Centro de rendimiento multicanal" in rendered
    assert "Salud de campaña" in rendered
    assert "Rendimiento por plataforma" in rendered
    assert "Evolución de resultados" in rendered
    assert "window.REPORT_DATA" in rendered
    assert ".textContent" in rendered
    assert "Number.isFinite" in rendered


def test_artz_template_hides_unavailable_sections_without_broken_or_external_assets():
    rendered = render_report("artz", {
        "meta": {"company_name": "Acme", "platforms": [], "period": {"start": "2026-07-01", "end": "2026-07-31"}},
        "summary": {}, "rates": {}, "deltas": {}, "by_platform": {}, "daily_series": [],
        "rows": {"current": [], "prior": [], "supplemental": []},
        "breakdowns": {}, "tables": {"export": []}, "narratives": [], "availability": {},
    })

    assert rendered.count('data-report-section="true" hidden') == 8
    assert 'showSection("audience-section", audienceRows.length > 0)' in rendered
    assert 'showSection("insights-section", narratives.length > 0)' in rendered
    assert "Datos no disponibles" not in rendered
    assert "innerHTML" not in rendered
    assert "contenteditable" not in rendered
    assert "downloadHTML" not in rendered
    assert "downloadPDF" not in rendered
    assert "openPin" not in rendered
    for forbidden_asset_or_request in (
        "<img", "<iframe", "src=", "href=", "fetch(", "XMLHttpRequest", "WebSocket",
        "window.open", "updateEmbed", "../ARTZ_files", "assets ARTZ", "http://", "https://",
    ):
        assert forbidden_asset_or_request not in rendered
    for leaked_identity in (
        "parmalat", "la lechera", "toni", "vita", "nutri", "shamuna", "adriana hoyos", "artz",
        "dra. gaby", "la toña", "yogurt fresa", "cumbayá",
    ):
        assert leaked_identity not in rendered.casefold()
