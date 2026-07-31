# Native Meta Result Cost and Budget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Meta detail table use Meta's native period Cost per result, show level-aware total-budget information, rename Inversión to Importe gastado, and keep CSV output identical to the rendered table.

**Architecture:** Reuse the dashboard's existing Meta Proxy calls. Extend aggregate Insights rows with native result/cost data, extend filter metadata with campaign/ad-set budgets, and pass both through one pure enrichment helper before the existing formatting, TOTAL-row, CSV, and rendering path.

**Tech Stack:** Python 3.14, pandas, Streamlit 1.58, pytest, existing Meta Proxy.

## Global Constraints

- Reuse the existing Meta Proxy; do not modify `app/`, backend connectors, API schemas, or dependencies.
- Keep the explicit **Aplicar filtros** interaction and current Campaign → Ad set → Ad hierarchy.
- Cost per result must come from Meta's period-level native `cost_per_result`; never reweight daily rows.
- Campaign budget: lifetime amount, `Presupuesto diario`, or `Se administra a nivel de conjuntos`.
- Ad-set budget: lifetime amount, `Presupuesto diario`, or `Se administra a nivel campaña`.
- Ad budget: show only `Se administra a nivel de conjuntos` or `Se administra a nivel campaña`; never repeat a parent amount.
- The TOTAL row sums numeric lifetime budgets only and averages available native Cost per result values.
- Final columns end with `Presupuesto`, `Importe gastado`.
- The CSV serializes the exact final DataFrame rendered by the Meta table.
- Preserve the pending light-theme sidebar reopen-button fix as its own rollback unit.
- Work on the existing `fixed-cards` branch. Do not push or deploy.

## File Map

| File | Responsibility in this change |
| --- | --- |
| `dashboard/api.py` | Fetch and normalize native aggregate result cost plus campaign/ad-set budget metadata through the existing proxy. |
| `dashboard/utils.py` | Apply budget ownership rules, merge native result cost by active identity, and build the mixed numeric/text TOTAL row. |
| `dashboard.py` | Select the active Meta level, reuse aggregate rows, order/rename columns, and feed one DataFrame to table and CSV. |
| `tests/test_dashboard_ui.py` | Functional API/helper regressions and focused dashboard wiring checks. |
| `tests/test_dashboard_exports.py` | Exact rendered-table/CSV parity check. |

**Review workload forecast:** Low risk, below 400 authored changed lines. Four independent work-unit commits are sufficient; no chained PR is needed.

---

### Task 1: Checkpoint the Existing Light-Theme Sidebar Fix

**Files:**
- Modify already present: `dashboard.py:586-587`
- Test already present: `tests/test_dashboard_ui.py:79-85`

**Interfaces:**
- Produces: a clean baseline commit containing only the already verified `stExpandSidebarButton` light-theme regression.
- Consumes: current uncommitted working-tree changes on `fixed-cards`.

- [ ] **Step 1: Confirm the rollback boundary**

Run:

```bash
git diff -- dashboard.py tests/test_dashboard_ui.py
```

Expected: only two production selector lines and the focused
`test_light_theme_styles_streamlit_expand_sidebar_button` test are present.

- [ ] **Step 2: Re-run the focused regression**

Run:

```bash
ENABLE_BIGQUERY_SINK=false .venv/bin/python -m pytest \
  tests/test_dashboard_ui.py::test_light_theme_styles_streamlit_expand_sidebar_button -q
```

Expected: `1 passed`. The original RED receipt was a missing
`stExpandSidebarButton` selector; no new test needs to be invented for this
checkpoint.

- [ ] **Step 3: Verify the existing dashboard suite**

Run:

```bash
ENABLE_BIGQUERY_SINK=false .venv/bin/python -m pytest \
  tests/test_dashboard_ui.py tests/test_dashboard_exports.py -q
.venv/bin/python -m py_compile dashboard.py
git diff --check
```

Expected: 50 tests pass, compilation exits `0`, and diff check has no findings.

- [ ] **Step 4: Commit the isolated fix**

```bash
git add dashboard.py tests/test_dashboard_ui.py
git commit -m "fix(dashboard): show sidebar reopen control in light mode"
```

Rollback boundary: reverting this commit removes only the current Streamlit
selector compatibility fix.

---

### Task 2: Fetch Native Period Result Cost and Budget Metadata

**Files:**
- Modify: `dashboard/api.py:126-220`
- Modify: `dashboard/api.py:321-374`
- Test: `tests/test_dashboard_ui.py:113-165`

**Interfaces:**
- Produces: `_meta_indicator_value(entries, indicator) -> float | None`.
- Produces: `_meta_minor_currency(value) -> float | None`.
- Extends: `fetch_meta_aggregate_insights(...) -> tuple[list[dict], str | None]` rows with `result_indicator`, `results`, and `cost_per_result`.
- Extends: `fetch_meta_filter_rows(...) -> tuple[list[dict], str | None]` rows with normalized `campaign_daily_budget`, `campaign_lifetime_budget`, `adset_daily_budget`, and `adset_lifetime_budget`.
- Consumes: existing `_meta_proxy_get()` and pagination behavior.

- [ ] **Step 1: Extend the aggregate Insights test for native result cost**

Add native result fields to the first response in
`test_meta_aggregate_insights_preserves_reach_and_paginates_actions`:

```python
"results": [{
    "indicator": "actions:lead",
    "values": [{"value": "5"}],
}],
"cost_per_result": [{
    "indicator": "actions:lead",
    "values": [{"value": "12.34"}],
}],
```

Add these assertions after the existing metric assertions:

```python
assert rows[0]["result_indicator"] == "actions:lead"
assert rows[0]["results"] == 5.0
assert rows[0]["cost_per_result"] == 12.34
requested_fields = calls[0]["params"]["fields"].split(",")
assert "results" in requested_fields
assert "cost_per_result" in requested_fields
assert "adset_id" in requested_fields
assert "adset_name" in requested_fields
```

- [ ] **Step 2: Write the failing budget-metadata test**

Add:

```python
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
```

- [ ] **Step 3: Run both tests to verify RED**

Run:

```bash
ENABLE_BIGQUERY_SINK=false .venv/bin/python -m pytest \
  tests/test_dashboard_ui.py::test_meta_aggregate_insights_preserves_reach_and_paginates_actions \
  tests/test_dashboard_ui.py::test_meta_filter_rows_include_normalized_campaign_and_adset_budgets -q
```

Expected: failures because aggregate rows lack native result keys and filter
rows lack normalized budget keys.

- [ ] **Step 4: Add the two minimal parsing helpers**

Add immediately below `_meta_proxy_get()` in `dashboard/api.py`:

```python
def _meta_indicator_value(entries, indicator):
    for entry in entries or []:
        if str(entry.get("indicator") or "") != indicator:
            continue
        values = entry.get("values") or []
        try:
            return float(values[0]["value"])
        except (IndexError, KeyError, TypeError, ValueError):
            return None
    return None


def _meta_minor_currency(value):
    if value in (None, ""):
        return None
    try:
        return float(value) / 100
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 5: Extend aggregate fields and normalized rows**

Start aggregate fields with native result metrics:

```python
fields = ["impressions", "reach", "results", "cost_per_result"]
if level in ("campaign", "adset", "ad"):
    fields += ["campaign_id", "campaign_name"]
if level in ("adset", "ad"):
    fields += ["adset_id", "adset_name"]
if level == "ad":
    fields += ["ad_id", "ad_name", "actions"]
```

Inside each aggregate Insight row, resolve and include the native values:

```python
result_entries = insight.get("results") or []
result_indicator = str(result_entries[0].get("indicator") or "") if result_entries else ""
result_value = _meta_indicator_value(result_entries, result_indicator)
result_cost = _meta_indicator_value(
    insight.get("cost_per_result"), result_indicator
)
```

Add these keys to the existing row dictionary:

```python
"adset_id": insight.get("adset_id") or "",
"adset_name": insight.get("adset_name") or "",
"result_indicator": result_indicator,
"results": result_value,
"cost_per_result": result_cost,
```

- [ ] **Step 6: Extend existing filter metadata without a new request path**

Change the existing nested fields string to:

```python
"fields": (
    "id,name,"
    "campaign{id,name,daily_budget,lifetime_budget},"
    "adset{id,name,daily_budget,lifetime_budget}"
),
```

Add normalized values to each filter row:

```python
"campaign_daily_budget": _meta_minor_currency(campaign.get("daily_budget")),
"campaign_lifetime_budget": _meta_minor_currency(campaign.get("lifetime_budget")),
"adset_daily_budget": _meta_minor_currency(adset.get("daily_budget")),
"adset_lifetime_budget": _meta_minor_currency(adset.get("lifetime_budget")),
```

- [ ] **Step 7: Run tests to verify GREEN**

Run:

```bash
ENABLE_BIGQUERY_SINK=false .venv/bin/python -m pytest \
  tests/test_dashboard_ui.py::test_meta_aggregate_insights_preserves_reach_and_paginates_actions \
  tests/test_dashboard_ui.py::test_meta_filter_rows_include_normalized_campaign_and_adset_budgets -q
```

Expected: `2 passed`.

- [ ] **Step 8: Commit the API data-source work unit**

```bash
git add dashboard/api.py tests/test_dashboard_ui.py
git commit -m "feat(dashboard): fetch native Meta costs and budgets"
```

Rollback boundary: reverting this commit restores the previous aggregate/filter
row shapes without changing the table.

---

### Task 3: Implement Level-Aware Budget and Native-Cost Enrichment

**Files:**
- Modify: `dashboard/utils.py:150-180`
- Test: `tests/test_dashboard_ui.py:330-450`

**Interfaces:**
- Produces: `meta_budget_display(level: str, metadata: dict | None) -> tuple[str, float]`.
- Produces: `enrich_meta_campaign_summary(frame: pd.DataFrame, aggregate_rows: list[dict], filter_rows: list[dict], level: str) -> pd.DataFrame`.
- Extends: `build_meta_campaign_total_row(frame, identity_labels=("Campaña",)) -> dict` with `Presupuesto` and `Importe gastado`.
- Consumes: normalized budget fields and native aggregate rows from Task 2.

- [ ] **Step 1: Write failing budget-display cases**

Add:

```python
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
```

- [ ] **Step 2: Write the failing enrichment test**

Add:

```python
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
```

- [ ] **Step 3: Update the TOTAL-row test before implementation**

Add `"budget_total": [1000.0, 250.0]` to
`test_campaign_total_row_uses_sums_and_average_cost`, then change its expected
last keys to:

```python
"Presupuesto": "$1,250.00",
"Importe gastado": "$200.00",
```

Remove the obsolete `result_cost_weighted` fixture column from both TOTAL-row
tests; the production calculation will no longer expose it.

Also update `test_campaign_total_row_supports_two_identity_columns` with a
`budget_total` column so the helper exercises the same schema.

- [ ] **Step 4: Run the helper tests to verify RED**

Run:

```bash
ENABLE_BIGQUERY_SINK=false .venv/bin/python -m pytest \
  tests/test_dashboard_ui.py -k \
  "meta_budget_display or meta_summary_enrichment or campaign_total_row" -q
```

Expected: failures because the two enrichment helpers do not exist and the
TOTAL row still emits `Inversión` without `Presupuesto`.

- [ ] **Step 5: Implement the budget display rules**

Add before `build_meta_campaign_total_row()`:

```python
def meta_budget_display(level, metadata):
    if metadata is None:
        return "N/D", 0.0

    campaign_lifetime = float(metadata.get("campaign_lifetime_budget") or 0)
    campaign_daily = float(metadata.get("campaign_daily_budget") or 0)
    adset_lifetime = float(metadata.get("adset_lifetime_budget") or 0)
    adset_daily = float(metadata.get("adset_daily_budget") or 0)

    if level == "campaign":
        if campaign_lifetime > 0:
            return f"${campaign_lifetime:,.2f}", campaign_lifetime
        if campaign_daily > 0:
            return "Presupuesto diario", 0.0
        return "Se administra a nivel de conjuntos", 0.0

    if level == "adset":
        if adset_lifetime > 0:
            return f"${adset_lifetime:,.2f}", adset_lifetime
        if adset_daily > 0:
            return "Presupuesto diario", 0.0
        return "Se administra a nivel campaña", 0.0

    if adset_lifetime > 0 or adset_daily > 0:
        return "Se administra a nivel de conjuntos", 0.0
    return "Se administra a nivel campaña", 0.0
```

- [ ] **Step 6: Implement one pure enrichment path**

Add:

```python
def enrich_meta_campaign_summary(frame, aggregate_rows, filter_rows, level):
    field_pairs = {
        "campaign": (("base_campaign_name", "campaign_name"),),
        "adset": (
            ("base_campaign_name", "campaign_name"),
            ("adset_name", "adset_name"),
        ),
        "ad": (("adset_name", "adset_name"), ("ad_name", "ad_name")),
    }[level]

    def record_key(record, summary_side):
        values = []
        for summary_field, meta_field in field_pairs:
            field = summary_field if summary_side else meta_field
            value = record.get(field, "")
            if meta_field == "campaign_name":
                value = meta_base_campaign_name(value)
            values.append(str(value))
        return tuple(values)

    native_by_key = {
        record_key(row, False): row
        for row in aggregate_rows
    }
    budget_by_key = {
        record_key(row, False): row
        for row in filter_rows
    }

    result = frame.copy()
    keys = [record_key(row, True) for _, row in result.iterrows()]
    result["cost_per_result"] = [
        (native_by_key.get(key) or {}).get("cost_per_result")
        for key in keys
    ]
    budget_values = [
        meta_budget_display(level, budget_by_key.get(key))
        for key in keys
    ]
    result["budget_display"] = [value[0] for value in budget_values]
    result["budget_total"] = [value[1] for value in budget_values]
    return result
```

- [ ] **Step 7: Extend the TOTAL helper**

Use numeric coercion so unavailable costs are ignored and text budget states
never enter arithmetic:

```python
cost_values = pd.to_numeric(frame["cost_per_result"], errors="coerce")
cost_per_result = cost_values.mean()
budget_total = pd.to_numeric(
    frame.get("budget_total", pd.Series(dtype=float)), errors="coerce"
).fillna(0).sum()
cost_display = (
    f"${cost_per_result:,.2f}" if pd.notna(cost_per_result) else "N/D"
)
```

Emit these final keys in `row.update()`:

```python
"Costo por resultado": cost_display,
"Presupuesto": f"${budget_total:,.2f}",
"Importe gastado": f"${total_spend:,.2f}",
```

Remove the old `"Inversión"` key.

- [ ] **Step 8: Run helper tests to verify GREEN**

Run:

```bash
ENABLE_BIGQUERY_SINK=false .venv/bin/python -m pytest \
  tests/test_dashboard_ui.py -k \
  "meta_budget_display or meta_summary_enrichment or campaign_total_row" -q
```

Expected: every selected helper test passes.

- [ ] **Step 9: Commit the pure reporting rules**

```bash
git add dashboard/utils.py tests/test_dashboard_ui.py
git commit -m "feat(dashboard): model Meta budget ownership"
```

Rollback boundary: reverting this commit removes the new pure enrichment and
TOTAL rules while leaving proxy response data available.

---

### Task 4: Wire Native Cost and Budget into Table and CSV

**Files:**
- Modify: `dashboard.py:1180-1250`
- Modify: `dashboard.py:1665-1760`
- Modify: `tests/test_dashboard_ui.py:500-660`
- Test: `tests/test_dashboard_exports.py:35-50`

**Interfaces:**
- Consumes: `enrich_meta_campaign_summary(...)` from Task 3.
- Consumes: extended campaign/ad aggregate rows and normalized filter rows from Task 2.
- Produces: one final `campaign_summary` with exact display/CSV columns and TOTAL row.

- [ ] **Step 1: Import the enrichment helper**

Add `enrich_meta_campaign_summary` to the existing `dashboard.utils` import in
`dashboard.py`.

- [ ] **Step 2: Write failing dashboard wiring assertions**

Update `test_featured_campaigns_show_requested_meta_metrics` so its expected
labels include:

```python
"Presupuesto",
"Importe gastado",
```

and no longer include `"Inversión"`.

Add:

```python
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
```

Extend `test_meta_campaign_csv_uses_the_displayed_table_data` with:

```python
assert '"budget_display": "Presupuesto"' in SOURCE
assert '"spend": "Importe gastado"' in SOURCE
```

- [ ] **Step 3: Run the wiring tests to verify RED**

Run:

```bash
ENABLE_BIGQUERY_SINK=false .venv/bin/python -m pytest \
  tests/test_dashboard_ui.py::test_featured_campaigns_show_requested_meta_metrics \
  tests/test_dashboard_ui.py::test_meta_table_uses_native_period_cost_and_level_budget \
  tests/test_dashboard_exports.py::test_meta_campaign_csv_uses_the_displayed_table_data -q
```

Expected: failures because the table still uses weighted daily cost and the old
column name.

- [ ] **Step 4: Select the active aggregate level once**

After applied filters are loaded, derive:

```python
meta_detail_level = "campaign"
if applied_adset_filter or applied_ad_filter != "Todos":
    meta_detail_level = "ad"
elif applied_campaign_filter:
    meta_detail_level = "adset"
```

Initialize `adset_aggregate_insights = []`. Replace the existing request tuple
with a request list that keeps the current consumers and adds ad-set data only
for the ad-set table level:

```python
adset_aggregate_insights = []
applied_aggregate_filters = {
    **aggregate_filters,
    **st.session_state.get("meta_applied_api_filters", {}),
}
aggregate_requests = [
    ("account", start_date, end_date, current_account_insights, aggregate_filters),
    ("account", prev_start_date, prev_end_date, previous_account_insights, aggregate_filters),
    ("campaign", start_date, end_date, campaign_aggregate_insights, aggregate_filters),
    ("ad", start_date, end_date, ad_aggregate_insights, aggregate_filters),
]
if meta_detail_level == "adset":
    aggregate_requests.append((
        "adset",
        start_date,
        end_date,
        adset_aggregate_insights,
        applied_aggregate_filters,
    ))

for insight_level, period_start, period_end, target, request_filters in aggregate_requests:
    insight_rows, insight_error = fetch_meta_aggregate_insights(
        client_id,
        account_id,
        period_start,
        period_end,
        insight_level,
        request_filters,
        api_key,
    )
    target.extend(insight_rows)
    if insight_error:
        aggregate_errors.append(insight_error)
```

- [ ] **Step 5: Remove the weighted daily-cost path**

In the first ads grouping, replace `result_cost_weighted` with a normal mean
that exists only as an intermediate schema value:

```python
"cost_per_result": "mean",
```

In the Meta identity grouping, retain `cost_per_result: "mean"` and remove all
`result_cost_weighted` creation, summation, and division. Task 3 overwrites the
intermediate value with the native aggregate value or `None`.

- [ ] **Step 6: Enrich before building TOTAL or formatting**

Choose the existing aggregate rows by level and enrich once:

```python
native_rows_by_level = {
    "campaign": campaign_aggregate_insights,
    "adset": adset_aggregate_insights,
    "ad": ad_aggregate_insights,
}
campaign_summary = enrich_meta_campaign_summary(
    campaign_summary,
    native_rows_by_level[meta_detail_level],
    filter_rows,
    meta_detail_level,
)
```

Keep `build_meta_campaign_total_row()` immediately after this enrichment and
before display formatting.

- [ ] **Step 7: Format and order the final table once**

Format native cost without inventing a zero:

```python
campaign_summary["cost_per_result"] = campaign_summary["cost_per_result"].apply(
    lambda value: f"${value:,.2f}" if pd.notna(value) else "N/D"
)
```

Keep `budget_display` already formatted. End the selected source columns with:

```python
"budget_display",
"spend",
```

and rename them with:

```python
"budget_display": "Presupuesto",
"spend": "Importe gastado",
```

Append the TOTAL row, assign `campaign_summary` to `csv_export_frame["frame"]`,
and render that same object exactly as today.

- [ ] **Step 8: Run the wiring tests to verify GREEN**

Run:

```bash
ENABLE_BIGQUERY_SINK=false .venv/bin/python -m pytest \
  tests/test_dashboard_ui.py::test_featured_campaigns_show_requested_meta_metrics \
  tests/test_dashboard_ui.py::test_meta_table_uses_native_period_cost_and_level_budget \
  tests/test_dashboard_exports.py::test_meta_campaign_csv_uses_the_displayed_table_data -q
```

Expected: `3 passed`.

- [ ] **Step 9: Run all scoped dashboard regressions**

Run:

```bash
ENABLE_BIGQUERY_SINK=false .venv/bin/python -m pytest \
  tests/test_dashboard_ui.py tests/test_dashboard_exports.py -q
.venv/bin/python -m py_compile dashboard.py dashboard/api.py dashboard/utils.py
git diff --check
```

Expected: zero failures, compilation exit `0`, and no diff-check findings.

- [ ] **Step 10: Commit the rendered table and CSV work unit**

```bash
git add dashboard.py tests/test_dashboard_ui.py tests/test_dashboard_exports.py
git commit -m "feat(dashboard): show native Meta cost and budgets"
```

Rollback boundary: reverting this commit restores the old table while leaving
the separately tested API and helper work units intact.

---

### Task 5: Final Verification

**Files:**
- Verify: `dashboard.py`
- Verify: `dashboard/api.py`
- Verify: `dashboard/utils.py`
- Verify: `tests/test_dashboard_ui.py`
- Verify: `tests/test_dashboard_exports.py`

**Interfaces:**
- Consumes: Tasks 1-4 committed state.
- Produces: verification evidence only; no code or deployment.

- [ ] **Step 1: Run the full scoped suite and compilation**

Run:

```bash
ENABLE_BIGQUERY_SINK=false .venv/bin/python -m pytest \
  tests/test_dashboard_ui.py tests/test_dashboard_exports.py -q
.venv/bin/python -m py_compile dashboard.py dashboard/api.py dashboard/utils.py
git diff --check
```

Expected: all scoped tests pass, compilation exits `0`, and diff check is clean.

- [ ] **Step 2: Verify requirements against source**

Run:

```bash
rg -n "result_cost_weighted|Presupuesto|Importe gastado|enrich_meta_campaign_summary|adset_aggregate_insights" \
  dashboard.py dashboard/utils.py tests/test_dashboard_ui.py tests/test_dashboard_exports.py
```

Expected:

- `result_cost_weighted` is absent from the active Meta table path.
- `Presupuesto` precedes `Importe gastado`.
- One enrichment call feeds both rendered table and CSV.
- Ad-set aggregate rows are requested only for the ad-set table level.

- [ ] **Step 3: Verify the implementation boundary and repository state**

Run:

```bash
git log --oneline --reverse dc1c297..HEAD
git diff --name-only dc1c297..HEAD
git status --short
```

Expected:

- One plan-document commit, one sidebar compatibility commit, and three Meta
  reporting work-unit commits.
- Changed implementation files are limited to dashboard code/tests plus this plan.
- No `app/` or connector changes.
- No uncommitted implementation files.
- No push or deployment.

Runtime harness: automated helper/API tests exercise the response boundaries;
live Meta calls are intentionally not run because they require the user's
account credentials. Visual validation remains local after implementation.
