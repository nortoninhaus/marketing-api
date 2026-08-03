# Meta Dynamic Campaign Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show every Meta campaign with its full name and the result value, cost, and official Spanish result label selected by Meta; rank the campaign cards by leads.

**Architecture:** Preserve Meta's raw result indicator in `MetaAdsConnector`, including an action/cost fallback when the Insights `results` pair is absent. Normalize that string through `dashboard/api.py`, translate it with one explicit official-label catalog, and keep presentation changes inside the existing Streamlit campaign section.

**Tech Stack:** Python 3.14 locally, FastAPI, Meta Business SDK, pandas, Streamlit, pytest.

## Global Constraints

- Use only official Meta Spanish labels; never humanize or guess an unknown indicator.
- Render `—` when the official-label catalog has no match.
- Remove the duplicated Reach column from the featured campaign table.
- Show every campaign and preserve its complete name.
- Keep exactly eight ranking cards, ordered descending by leads, and show leads on each card.
- Do not add dependencies or perform unrelated refactors.
- Keep dashboard changes local: do not push or deploy the dashboard service.
- Run `deploy.sh` only because this plan changes backend code.

---

### Task 1: Preserve Meta's matching result indicator, value, and cost

**Files:**
- Modify: `app/connectors/meta.py:30-392`
- Test: `tests/test_meta.py:48-95`

**Interfaces:**
- Consumes: one Insights row containing `results`, `cost_per_result`, `actions`, `cost_per_action_type`, `objective`, and `optimization_goal`.
- Produces in `CampaignData.metrics`: `result_indicator: str`, `__results__: float`, and `cost_per_result: float`.

- [ ] **Step 1: Extend the explicit-results regression test**

Update `test_meta_ads_maps_results_alias` so the returned row must preserve the indicator:

```python
assert rows[0].metrics["result_indicator"] == "actions:lead"
assert rows[0].metrics["__results__"] == 12
assert rows[0].metrics["cost_per_result"] == 0.42
```

- [ ] **Step 2: Add a failing action-based lead test**

Add a second test whose mock Insights row has no `results` pair:

```python
@patch("app.connectors.meta.FacebookSession")
@patch("app.connectors.meta.FacebookAdsApi")
@patch("app.connectors.meta.AdAccount")
def test_meta_ads_resolves_lead_result_from_actions(
    mock_ad_account, mock_api, mock_session
):
    account = MagicMock()
    mock_ad_account.return_value = account
    account.get_insights.return_value = [{
        "campaign_name": "Quality Leads",
        "date_start": "2026-07-01",
        "objective": "OUTCOME_LEADS",
        "optimization_goal": "QUALITY_LEAD",
        "actions": [{"action_type": "lead", "value": "9"}],
        "cost_per_action_type": [{"action_type": "lead", "value": "3.25"}],
    }]

    connector = MetaAdsConnector()
    with patch.object(connector, "get_credentials", return_value={
        "access_token": "fake_ads_token",
        "ad_account_id": "act_12345",
    }):
        rows = connector.fetch_data(DataRequest(
            platform="meta_ads",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            metrics=["__results__", "cost_per_result", "lead"],
            client_id="test_client",
            user_id="test_user",
            account_id="act_12345",
        ))

    assert rows[0].metrics["result_indicator"] == "actions:lead"
    assert rows[0].metrics["__results__"] == 9
    assert rows[0].metrics["cost_per_result"] == 3.25
```

Reuse the test's existing connector/request setup instead of adding production-only injection.

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest \
  tests/test_meta.py::test_meta_ads_maps_results_alias \
  tests/test_meta.py::test_meta_ads_resolves_lead_result_from_actions -q
```

Expected: both tests fail because `result_indicator` is not returned and the action-based row has no resolved result cost.

- [ ] **Step 4: Request the minimum supporting Meta fields**

When `__results__` or `cost_per_result` is requested, include these Insights fields once:

```python
for result_field in (
    "results",
    "cost_per_result",
    "actions",
    "cost_per_action_type",
    "objective",
    "optimization_goal",
):
    if result_field not in fields:
        fields.append(result_field)
```

- [ ] **Step 5: Resolve one result pair per Insights row**

Before the request-metric loop, resolve the row once:

```python
result_indicator, result_value, result_cost = _resolve_meta_result(i)
```

The helper must:

1. Prefer the first `results` entry and match its `indicator` against `cost_per_result`.
2. Otherwise select an action type using `optimization_goal` first and `objective` second.
3. Match the chosen action type exactly in `actions` and `cost_per_action_type`.
4. Return `("", 0.0, 0.0)` when no supported pair exists.

Use these ordered action candidates:

```python
RESULT_ACTIONS_BY_OPTIMIZATION = {
    "QUALITY_LEAD": ("lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead"),
    "LEAD_GENERATION": ("lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead"),
    "LANDING_PAGE_VIEWS": ("landing_page_view",),
    "LINK_CLICKS": ("link_click",),
    "POST_ENGAGEMENT": ("post_engagement",),
    "THRUPLAY": ("video_view",),
    "APP_INSTALLS": ("app_install",),
    "CONVERSATIONS": (
        "onsite_conversion.messaging_conversation_started_7d",
        "messaging_conversation_started_7d",
    ),
    "OFFSITE_CONVERSIONS": ("offsite_conversion.fb_pixel_purchase", "purchase"),
}

RESULT_ACTIONS_BY_OBJECTIVE = {
    "OUTCOME_LEADS": ("lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead"),
    "OUTCOME_TRAFFIC": ("landing_page_view", "link_click"),
    "OUTCOME_ENGAGEMENT": (
        "post_engagement",
        "onsite_conversion.messaging_conversation_started_7d",
        "messaging_conversation_started_7d",
    ),
    "OUTCOME_SALES": ("offsite_conversion.fb_pixel_purchase", "purchase"),
    "OUTCOME_APP_PROMOTION": ("app_install",),
}
```

Store fallback action indicators as `actions:<action_type>`. Do not pick an arbitrary action outside these ordered candidates.

- [ ] **Step 6: Return the resolved fields**

For requested `__results__` and `cost_per_result`, use the resolved values instead of reparsing the nested arrays, and always add:

```python
metrics_dict["result_indicator"] = result_indicator
```

- [ ] **Step 7: Run connector tests and verify GREEN**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_meta.py -q
.venv/bin/python -m py_compile app/connectors/meta.py tests/test_meta.py
```

Expected: every command exits `0`.

- [ ] **Step 8: Commit the backend work unit**

```bash
git add app/connectors/meta.py tests/test_meta.py
git diff --cached --check
git commit -m "fix(meta): preserve campaign result metric"
```

Rollback boundary: this commit alone removes result-indicator preservation and action-based result/cost resolution.

---

### Task 2: Normalize and officially translate the indicator

**Files:**
- Modify: `dashboard/config.py`
- Modify: `dashboard/utils.py`
- Modify: `dashboard/api.py:257-336`
- Test: `tests/test_dashboard_ui.py:104-170`

**Interfaces:**
- Consumes: `metrics["result_indicator"]` from Task 1.
- Produces: a `result_indicator` DataFrame column and `translate_meta_result_indicator(value) -> str`.

- [ ] **Step 1: Add failing normalization and translation tests**

```python
def test_meta_result_indicator_survives_dashboard_normalization():
    df = process_api_response([{
        "campaign_name": "Reach Campaign",
        "date": "2026-07-01",
        "metrics": {
            "result_indicator": "reach",
            "__results__": 42_206,
            "cost_per_result": 0.01,
        },
    }], "meta_ads", "client_1", "user_1")

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
    assert translate_meta_result_indicator(indicator) == label


def test_unknown_meta_result_indicator_is_not_humanized():
    assert translate_meta_result_indicator("actions:future_metric") == "—"
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_dashboard_ui.py \
  -k "result_indicator or result_indicators" -q
```

Expected: failures because neither the normalized column nor translation helper exists.

- [ ] **Step 3: Add the official-label catalog**

Add one `META_RESULT_LABELS` dictionary in `dashboard/config.py`. Include only verified Meta terminology:

```python
META_RESULT_LABELS = {
    "reach": "Alcance",
    "actions:lead": "Clientes potenciales",
    "actions:onsite_conversion.lead_grouped": "Clientes potenciales",
    "actions:offsite_conversion.fb_pixel_lead": "Clientes potenciales",
    "actions:post_engagement": "Interacciones con la publicación",
    "actions:landing_page_view": "Visitas a la página de destino",
    "actions:link_click": "Clics en el enlace",
    "actions:purchase": "Compras",
    "actions:offsite_conversion.fb_pixel_purchase": "Compras",
    "actions:app_install": "Instalaciones de la app",
    "actions:video_view": "Reproducciones de video de 3 segundos",
    "actions:onsite_conversion.messaging_conversation_started_7d": "Conversaciones con mensajes iniciadas",
    "actions:messaging_conversation_started_7d": "Conversaciones con mensajes iniciadas",
}
```

- [ ] **Step 4: Add the strict translation helper**

In `dashboard/utils.py`:

```python
def translate_meta_result_indicator(value):
    return META_RESULT_LABELS.get(str(value or "").lower(), "—")
```

Do not add title-casing, underscore replacement, or any other fallback.

- [ ] **Step 5: Preserve the indicator in API normalization**

In `process_api_response`, add:

```python
result_indicator = str(metrics.get("result_indicator") or "")
```

Store it in each row and include it in the empty DataFrame schema.

- [ ] **Step 6: Run focused tests and verify GREEN**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_dashboard_ui.py \
  -k "result_indicator or result_indicators" -q
.venv/bin/python -m py_compile dashboard/config.py dashboard/utils.py dashboard/api.py
```

Expected: every command exits `0`.

- [ ] **Step 7: Commit the dashboard data work unit locally**

```bash
git add dashboard/config.py dashboard/utils.py dashboard/api.py tests/test_dashboard_ui.py
git diff --cached --check
git commit -m "feat(dashboard): translate Meta result indicators"
```

Rollback boundary: this commit removes only indicator normalization and the strict official-label catalog.

---

### Task 3: Show all campaigns and rank cards by leads

**Files:**
- Modify: `dashboard.py:89,948-1045,1594-1725`
- Test: `tests/test_dashboard_ui.py:104-200`

**Interfaces:**
- Consumes: normalized `result_indicator`, `results`, `cost_per_result`, and `lead` columns.
- Produces: the complete featured campaign table and eight lead-ranked cards.

- [ ] **Step 1: Replace the featured-campaign source assertions**

Update the UI test to require:

```python
featured_campaign_source = SOURCE[
    SOURCE.index("campaign_summary ="):
    SOURCE.index("preview_names =")
]

assert "DASHBOARD_CACHE_VERSION = 3" in SOURCE
assert 'frame["result_indicator"] = ""' in SOURCE
assert 'translate_meta_result_indicator' in SOURCE
assert '"reach": "Reach"' not in featured_campaign_source
assert '.sort_values("lead", ascending=False).head(8)' in SOURCE
assert "Ranking: top campañas por clientes potenciales (Meta)" in SOURCE
assert "<span>Clientes potenciales</span>" in SOURCE
```

Also assert the full-table aggregation is independent from `ranked_campaigns`, so the table is not limited to eight rows, and that display names use `base_campaign_name` rather than `clean_campaign_name`.

- [ ] **Step 2: Run the focused UI test and verify RED**

```bash
PYTHONPATH=. .venv/bin/pytest \
  tests/test_dashboard_ui.py::test_featured_campaigns_show_requested_meta_metrics \
  tests/test_dashboard_ui.py::test_results_schema_change_invalidates_and_migrates_cached_frames -q
```

Expected: failures on cache version, Reach removal, lead sorting, and lead card copy.

- [ ] **Step 3: Invalidate cached frames**

Set:

```python
DASHBOARD_CACHE_VERSION = 3
```

For both current and previous frames, add an empty `result_indicator` column when it is missing.

- [ ] **Step 4: Build the complete featured campaign table**

Aggregate all `meta_table` rows by full base campaign name, platform, and result indicator. Calculate numeric totals, use a result-weighted mean for the matching cost, and translate the indicator with `translate_meta_result_indicator`.

Use one temporary weighted column before grouping:

```python
meta_table["result_cost_weighted"] = (
    meta_table["results"] * meta_table["cost_per_result"]
)
campaign_summary = meta_table.groupby([
    "base_campaign_name", "platform", "result_indicator"
]).agg({
    "results": "sum",
    "result_cost_weighted": "sum",
    "spend": "sum",
    "impressions": "sum",
    "clicks": "sum",
}).reset_index()
campaign_summary["cost_per_result"] = (
    campaign_summary["result_cost_weighted"]
    .div(campaign_summary["results"])
    .where(campaign_summary["results"].gt(0), 0)
)
```

Render these columns only:

```text
Campaña
Plataforma
Tipo de resultado
Resultados
Costo por resultado
CPM
Impresiones
Clics
CPC
Inversión
```

Do not call `.head()` on this table and do not call `clean_campaign_name` for its campaign value.

- [ ] **Step 5: Rank only the cards by leads**

Build `ranked_campaigns` separately:

```python
ranked_campaigns = (
    meta_table.groupby("base_campaign_name")
    .agg({
        "lead": "sum",
        "spend": "sum",
        "impressions": "sum",
        "clicks": "sum",
        "conversions": "sum",
    })
    .reset_index()
    .sort_values("lead", ascending=False)
    .head(8)
)
```

Set the title exactly to:

```text
Ranking: top campañas por clientes potenciales (Meta)
```

Use the complete escaped `base_campaign_name` in cards and add:

```html
<div><span>Clientes potenciales</span><b>{row.lead:,.0f}</b></div>
```

- [ ] **Step 6: Run focused and full dashboard tests**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_dashboard_ui.py -q
.venv/bin/python -m py_compile dashboard.py tests/test_dashboard_ui.py
git diff --check
```

Expected: every command exits `0`.

- [ ] **Step 7: Commit the UI work unit locally**

```bash
git add dashboard.py tests/test_dashboard_ui.py
git diff --cached --check
git commit -m "feat(dashboard): rank Meta campaigns by leads"
```

Rollback boundary: this commit restores the prior top-results table/cards without touching backend result resolution.

---

### Task 4: Verify, synchronize main, and deploy only the backend service

**Files:**
- Verify: `app/connectors/meta.py`
- Verify locally only: `dashboard.py`, `dashboard/api.py`, `dashboard/config.py`, `dashboard/utils.py`
- Execute: `deploy.sh`

- [ ] **Step 1: Run the relevant complete test set**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_meta.py tests/test_dashboard_ui.py -q
.venv/bin/python -m py_compile \
  app/connectors/meta.py dashboard.py dashboard/api.py dashboard/config.py dashboard/utils.py
git diff --check
git status --short
```

Expected: tests pass, compilation exits `0`, and the worktree contains no uncommitted implementation files.

- [ ] **Step 2: Synchronize the branch with main without pushing**

```bash
git pull origin main
```

If this creates a merge, rerun Step 1. Do not run `git push`.

- [ ] **Step 3: Deploy the backend**

```bash
./deploy.sh
```

Expected: Cloud Build succeeds and Cloud Run reports a successful revision for `inhaus-marketing-api`.

- [ ] **Step 4: Verify the deployed backend response**

Run one authenticated campaign-data request for Meta and confirm each returned row contains:

```json
{
  "metrics": {
    "result_indicator": "reach",
    "__results__": 42206,
    "cost_per_result": 0.01
  }
}
```

The exact indicator and numbers depend on the campaign. Record the deployed Cloud Run revision. Do not deploy the dashboard.
