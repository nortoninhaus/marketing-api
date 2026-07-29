# Three Meta Campaign Rankings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the single Meta campaign ranking with separate top-three rankings for leads, reach, and interactions.

**Architecture:** Expose Meta's existing `post_engagement` action through the connector schema, normalize it into the dashboard frame, then aggregate one campaign summary and derive three sorted views from it. Reuse one deduplicated preview fetch and the existing card HTML.

**Tech Stack:** Python 3.14, FastAPI connector layer, pandas, Streamlit, pytest.

## Global Constraints

- Rankings remain campaign-level, aggregated by base campaign name across publisher platforms.
- Each ranking shows at most three campaigns in three columns.
- The ranking metric is the first metric row in its cards.
- Add no dependency or endpoint.
- Do not push or deploy the dashboard.
- Do not deploy the backend; the user will upload it manually.

---

### Task 1: Expose Meta post engagement

**Files:**
- Modify: `app/connectors/meta.py:430-470`
- Test: `tests/test_meta.py`

**Interfaces:**
- Consumes: Meta Insights `actions` entries whose `action_type` is `post_engagement`.
- Produces: `MetaAdsConnector.get_schema()["metrics"]` includes `post_engagement`; `fetch_data()` returns it in `CampaignData.metrics`.

- [ ] **Step 1: Write the failing connector test**

Add this test to `tests/test_meta.py`:

```python
@patch("app.connectors.meta.FacebookSession")
@patch("app.connectors.meta.FacebookAdsApi")
@patch("app.connectors.meta.AdAccount")
def test_meta_ads_exposes_post_engagement(
    mock_ad_account, mock_api, mock_session
):
    mock_instance = MagicMock()
    mock_ad_account.return_value = mock_instance
    mock_instance.get_insights.return_value = [{
        "campaign_name": "Engagement Campaign",
        "date_start": "2026-07-01",
        "actions": [
            {"action_type": "post_engagement", "value": "37"},
        ],
    }]

    connector = MetaAdsConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_ads_token",
            "ad_account_id": "act_12345",
        }
        request = DataRequest(
            platform="meta_ads",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            metrics=["post_engagement"],
            client_id="test_client",
            user_id="test_user",
            account_id="act_12345",
        )

        result = connector.fetch_data(request)

    assert "post_engagement" in connector.get_schema()["metrics"]
    assert result[0].metrics["post_engagement"] == 37
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_meta.py::test_meta_ads_exposes_post_engagement
```

Expected: FAIL because `post_engagement` is absent from the connector schema.

- [ ] **Step 3: Add the metric to the existing schema**

In `MetaAdsConnector.get_schema()`, add the metric beside the other action-backed metrics:

```python
"purchase",
"lead",
"post_engagement",
"add_to_cart",
```

Do not add parser code. The existing custom-action branch already requests `actions` and matches `post_engagement`.

- [ ] **Step 4: Verify the connector**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_meta.py::test_meta_ads_exposes_post_engagement
.venv/bin/python -m pytest -q tests/test_meta.py
```

Expected: both commands PASS.

- [ ] **Step 5: Commit the backend work unit**

```bash
git add app/connectors/meta.py tests/test_meta.py
git commit --no-verify -m "feat(meta): expose post engagement metric"
```

---

### Task 2: Normalize Meta interactions in the dashboard

**Files:**
- Modify: `dashboard/api.py:257-338`
- Modify: `dashboard.py:90,942-958,1041-1048`
- Test: `tests/test_dashboard_ui.py`

**Interfaces:**
- Consumes: API metric `post_engagement`.
- Produces: numeric `post_engagement` column in current and previous dashboard frames.

- [ ] **Step 1: Write the failing normalization test**

Add to `tests/test_dashboard_ui.py`:

```python
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
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_dashboard_ui.py::test_meta_post_engagement_is_requested_and_normalized
```

Expected: FAIL because `process_api_response()` does not create `post_engagement`.

- [ ] **Step 3: Normalize the metric**

In `dashboard/api.py`, extract and store the value:

```python
post_engagement = extract_metric(metrics, ["post_engagement"])
```

Add it to each row and the empty-frame columns:

```python
"post_engagement": int(post_engagement),
```

```python
"engagement", "post_engagement", "followers", "reach", "likes", "comments"
```

In `dashboard.py`, add `post_engagement` to the Meta Ads standard metrics:

```python
standard_metrics = [
    "impressions", "clicks", "spend", "conversions", "lead", "reach",
    "post_engagement", "__results__", "cost_per_result",
]
```

Migrate cached frames and invalidate old schema/query entries:

```python
DASHBOARD_CACHE_VERSION = 4
```

```python
if "post_engagement" not in frame.columns:
    frame["post_engagement"] = 0
```

- [ ] **Step 4: Verify dashboard normalization**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_dashboard_ui.py::test_meta_post_engagement_is_requested_and_normalized
.venv/bin/python -m pytest -q tests/test_dashboard_ui.py
```

Expected: both commands PASS after updating any cache-version assertion from `3` to `4`.

- [ ] **Step 5: Commit the dashboard data work unit**

```bash
git add dashboard.py dashboard/api.py tests/test_dashboard_ui.py
git commit --no-verify -m "feat(dashboard): load Meta post engagement"
```

---

### Task 3: Render three top-three campaign rankings

**Files:**
- Modify: `dashboard.py:1674-1742`
- Test: `tests/test_dashboard_ui.py:204-208`

**Interfaces:**
- Consumes: campaign columns `lead`, `reach`, `post_engagement`, `spend`, `impressions`, `clicks`, and `conversions`.
- Produces: three stacked ranking sections and one deduplicated preview request.

- [ ] **Step 1: Replace the old structural test with a failing three-ranking test**

Replace `test_meta_campaign_cards_rank_by_leads_and_keep_full_names` with:

```python
def test_meta_campaign_cards_render_three_top_three_rankings():
    ranking_source = SOURCE[
        SOURCE.index("ranking_specs ="):SOURCE.index("for preview in previews:")
    ]

    for title, metric, label in (
        ("clientes potenciales", "lead", "Clientes potenciales"),
        ("alcance", "reach", "Alcance"),
        ("interacciones", "post_engagement", "Interacciones"),
    ):
        assert f'("{title}", "{metric}", "{label}")' in ranking_source

    assert ".head(3)" in ranking_source
    assert "rank_cols = st.columns(3)" in ranking_source
    assert "metric_rows = [(metric_label," in ranking_source
    assert "campaign_name = html.escape(str(row.base_campaign_name))" in ranking_source
```

Use a direct assertion for the dynamic heading in the final test:

```python
assert 'st.markdown(f"### Ranking: top campañas por {ranking_name} (Meta)")' in ranking_source
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_dashboard_ui.py::test_meta_campaign_cards_render_three_top_three_rankings
```

Expected: FAIL because the current source has one lead ranking, eight cards, and four columns.

- [ ] **Step 3: Build three ranked views from one campaign summary**

Replace the current `ranked_campaigns` aggregation with:

```python
ranking_specs = (
    ("clientes potenciales", "lead", "Clientes potenciales"),
    ("alcance", "reach", "Alcance"),
    ("interacciones", "post_engagement", "Interacciones"),
)
campaign_ranking_summary = (
    meta_table.groupby("base_campaign_name")
    .agg(
        platform=("platform", lambda values: " / ".join(dict.fromkeys(values))),
        lead=("lead", "sum"),
        reach=("reach", "sum"),
        post_engagement=("post_engagement", "sum"),
        spend=("spend", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        conversions=("conversions", "sum"),
    )
    .reset_index()
)
ranked_campaigns_by_metric = {
    metric: campaign_ranking_summary.sort_values(metric, ascending=False).head(3)
    for _, metric, _ in ranking_specs
}
preview_names = tuple(dict.fromkeys(
    campaign_name
    for _, metric, _ in ranking_specs
    for campaign_name in ranked_campaigns_by_metric[metric]["base_campaign_name"]
))
```

Keep the existing preview cache and `previews_by_campaign` logic immediately after this block.

- [ ] **Step 4: Render each ranking with its metric first**

Wrap the current card loop with:

```python
if preview_error:
    st.info(preview_error)

for ranking_name, metric, metric_label in ranking_specs:
    st.markdown(f"### Ranking: top campañas por {ranking_name} (Meta)")
    ranked_campaigns = ranked_campaigns_by_metric[metric]
    rank_cols = st.columns(3)

    for idx, row in enumerate(ranked_campaigns.itertuples(index=False), start=1):
        preview = previews_by_campaign.get(row.base_campaign_name)
        ctr = row.clicks / row.impressions if row.impressions else 0
        cpc = row.spend / row.clicks if row.clicks else 0
        cpa = row.spend / row.conversions if row.conversions else 0

        metric_rows = [(metric_label, f"{getattr(row, metric):,.0f}")]
        metric_rows.extend([
            ("Inversión", f"${row.spend:,.2f}"),
            ("Conversiones", f"{row.conversions:,.0f}"),
        ])
        if metric != "lead":
            metric_rows.append(("Clientes potenciales", f"{row.lead:,.0f}"))
        metric_rows.extend([
            ("Clics", f"{row.clicks:,.0f}"),
            ("Impresiones", f"{row.impressions:,.0f}"),
            ("CTR", f"{ctr:.2%}"),
            ("CPC", f"${cpc:,.2f}"),
            ("CPA", f"${cpa:,.2f}"),
        ])
        metrics_html = "".join(
            '<div style="display:flex;justify-content:space-between;'
            'border-bottom:1px dashed #e5e7eb;padding-bottom:6px;">'
            f"<span>{label}</span><b>{value}</b></div>"
            for label, value in metric_rows
        )
```

Place `metrics_html` inside the existing card's metric container. Keep preview fallback, source badge, campaign name, ad name, CTR/CPC/CPA calculations, and `components.html()` unchanged except for using three columns.

- [ ] **Step 5: Verify all affected behavior**

Run:

```bash
.venv/bin/python -m pytest -q \
  tests/test_meta.py \
  tests/test_dashboard_ui.py
.venv/bin/python -c "from pathlib import Path; compile(Path('dashboard.py').read_text(), 'dashboard.py', 'exec'); compile(Path('dashboard/api.py').read_text(), 'dashboard/api.py', 'exec')"
git diff --check
```

Expected: all tests PASS, both dashboard files compile, and `git diff --check` reports nothing.

Runtime harness:

```bash
streamlit run dashboard.py
```

Verify with a Meta Ads account that each section shows no more than three campaigns, is sorted by its title metric, and displays that metric first. Stop the local server after verification.

If no Meta credentials are available, record the runtime harness as `N/A — requires the user's Meta account`; do not invent production evidence.

- [ ] **Step 6: Commit the ranking work unit**

```bash
git add dashboard.py tests/test_dashboard_ui.py
git commit --no-verify -m "feat(dashboard): add three Meta campaign rankings"
```

## Rollback

- Revert the three feature commits in reverse order.
- This removes `post_engagement` exposure, dashboard normalization, and the three ranking sections without affecting campaign filters or featured performance.

## Delivery

- Leave all commits on the current local branch.
- Do not push, deploy, or run `deploy.sh`.
- Tell the user that `app/connectors/meta.py` must be uploaded manually before interaction rankings receive production data.
