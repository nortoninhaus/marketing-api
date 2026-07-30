# Meta Detail Table Drill-Down Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task by task.

**Goal:** Make the Meta detail table show campaigns, campaign ad sets, or
ad-set ads according to the applied filter hierarchy.

**Architecture:** For applied campaigns, reuse the existing scoped detail query
to obtain `adset_name` and `ad_name` dimensions in `df_curr`. A small pure configuration helper
selects identity columns and the section title from applied filters; the
existing aggregation, formatting, TOTAL-row, HTML table, and deferred CSV path
then consume that configuration.

**Tech Stack:** Python 3.14, pandas, Streamlit, pytest.

## Global Constraints

- Keep the explicit **Aplicar filtros** button.
- Derive the table level from applied session-state filters, not transient
  widget values.
- No filters: `Campaña`.
- Applied campaign filters: `Campaña`, `Conjunto de anuncios`.
- Applied ad-set filters or a specific ad: `Conjunto de anuncios`, `Anuncio`.
- Keep all existing metric, sorting, formatting, and TOTAL-row behavior.
- The Meta CSV must serialize the exact DataFrame rendered by the table.
- Do not change KPI cards, rankings, backend code, connectors, or dependencies.
- Campaign-only drill-down may execute the existing scoped detail query once
  more; preserve its existing campaign filter scoping.
- Work on the existing `fixed-cards` branch.
- Do not push or deploy.
- Preserve the existing local TOTAL-row and CSV changes as their own rollback
  unit before implementing drill-down.

---

### Task 1: Checkpoint the Approved Local TOTAL and CSV Work

**Files:**

- Existing modifications: `dashboard.py`
- Existing modifications: `dashboard/ui.py`
- Existing modifications: `dashboard/utils.py`
- Existing modifications: `tests/test_dashboard_exports.py`
- Existing modifications: `tests/test_dashboard_ui.py`

**Interfaces:**

- Produces: a clean baseline commit containing the already-approved TOTAL-row
  colspan, Results sum, Cost-per-result mean, and table/CSV parity.
- Consumes: the current uncommitted working-tree changes on `fixed-cards`.

- [ ] **Step 1: Confirm only the approved baseline behavior is present**

Run:

```bash
git diff -- dashboard.py dashboard/ui.py dashboard/utils.py \
  tests/test_dashboard_exports.py tests/test_dashboard_ui.py
```

Expected:

- `TOTAL` spans two cells.
- Results are summed.
- Cost per result is an arithmetic mean.
- The deferred CSV holder receives `campaign_summary`.
- No hierarchical drill-down code exists yet.

- [ ] **Step 2: Re-run the baseline tests**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_dashboard_exports.py tests/test_dashboard_ui.py -q
.venv/bin/python -m py_compile dashboard.py dashboard/ui.py dashboard/utils.py
git diff --check
```

Expected: all tests pass, compilation exits `0`, and `git diff --check`
produces no findings. The current baseline is 42 passing tests.

- [ ] **Step 3: Commit the baseline work unit**

Run:

```bash
git add dashboard.py dashboard/ui.py dashboard/utils.py \
  tests/test_dashboard_exports.py tests/test_dashboard_ui.py
git commit --no-verify -m "feat(dashboard): align campaign totals and CSV export"
```

Expected: one commit containing only the approved table-total and CSV changes.

Rollback boundary: this is the drill-down feature's baseline dependency.
Revert the Task 2 feature commit first, then revert this commit to remove the
TOTAL-row presentation and CSV parity changes while retaining the design docs.

---

### Task 2: Implement Applied-Filter Table Drill-Down

**Files:**

- Modify: `dashboard/utils.py`
- Modify: `dashboard.py:74-83`
- Modify: `dashboard.py:1665-1734`
- Modify: `tests/test_dashboard_ui.py`

**Interfaces:**

- Produces:
  `meta_detail_table_config(campaign_filter, adset_filter, ad_filter, available_columns) -> tuple[tuple[tuple[str, str], ...], str]`
- Produces:
  `build_meta_campaign_total_row(frame, identity_labels=("Campaña",)) -> dict`
- Consumes: applied Meta filter values already loaded into
  `applied_campaign_filter`, `applied_adset_filter`, and `applied_ad_filter`.
- Consumes: `adset_name` and `ad_name` already requested by the detail query.
- The first tuple returned by `meta_detail_table_config` contains
  `(source_column, display_label)` pairs; the second value is the Spanish
  section title.

- [ ] **Step 1: Write failing hierarchy-configuration tests**

Add these tests to `tests/test_dashboard_ui.py`:

```python
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
```

- [ ] **Step 2: Write the failing dynamic TOTAL-label test**

Add:

```python
def test_campaign_total_row_supports_two_identity_columns():
    frame = pd.DataFrame({
        "results": [10, 30],
        "cost_per_result": [2, 4],
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
```

- [ ] **Step 3: Run the utility tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_ui.py \
  -k "meta_detail_table_config or campaign_total_row_supports_two" -v
```

Expected:

- `AttributeError` because `meta_detail_table_config` does not exist.
- `TypeError` because `build_meta_campaign_total_row` does not yet accept
  `identity_labels`.

- [ ] **Step 4: Implement the minimum hierarchy configuration**

Add to `dashboard/utils.py` immediately before
`build_meta_campaign_total_row`:

```python
def meta_detail_table_config(
    campaign_filter,
    adset_filter,
    ad_filter,
    available_columns,
):
    campaign_config = (
        (("base_campaign_name", "Campaña"),),
        "Detalle de Campañas y Resultados",
    )
    if adset_filter or ad_filter != "Todos":
        identity_columns = (
            ("adset_name", "Conjunto de anuncios"),
            ("ad_name", "Anuncio"),
        )
        title = "Detalle de Anuncios y Resultados"
    elif campaign_filter:
        identity_columns = (
            ("base_campaign_name", "Campaña"),
            ("adset_name", "Conjunto de anuncios"),
        )
        title = "Detalle de Conjuntos de anuncios y Resultados"
    else:
        return campaign_config

    if not all(column in available_columns for column, _ in identity_columns):
        return campaign_config
    return identity_columns, title
```

- [ ] **Step 5: Generalize the existing TOTAL-row identity cells**

Change the helper signature and return construction:

```python
def build_meta_campaign_total_row(frame, identity_labels=("Campaña",)):
    total_results = frame["results"].sum()
    total_spend = frame["spend"].sum()
    total_impressions = frame["impressions"].sum()
    total_clicks = frame["clicks"].sum()
    cost_per_result = frame["cost_per_result"].mean()
    cpm = total_spend * 1000 / total_impressions if total_impressions > 0 else 0
    cpc = total_spend / total_clicks if total_clicks > 0 else 0

    row = {label: "" for label in identity_labels}
    row[identity_labels[0]] = "TOTAL"
    row.update({
        "Tipo de resultado": "",
        "Resultados": f"{total_results:,.0f}",
        "Costo por resultado": f"${cost_per_result:,.2f}",
        "CPM": f"${cpm:,.2f}",
        "Impresiones": f"{total_impressions:,.0f}",
        "Clics": f"{total_clicks:,.0f}",
        "CPC": f"${cpc:,.2f}",
        "Inversión": f"${total_spend:,.2f}",
    })
    return row
```

- [ ] **Step 6: Run the utility tests and verify GREEN**

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_ui.py \
  -k "meta_detail_table_config or campaign_total_row" -v
```

Expected: all selected tests pass, including the existing TOTAL-row
regressions.

- [ ] **Step 7: Write a failing dashboard-wiring test**

Add:

```python
def test_meta_detail_table_uses_dynamic_identity_columns():
    detail_source = SOURCE[
        SOURCE.index("# CAMPAIGN BREAKDOWN TABLE"):
        SOURCE.index("ranking_specs = (")
    ]

    assert "meta_detail_table_config(" in detail_source
    assert "applied_campaign_filter" in detail_source
    assert "applied_adset_filter" in detail_source
    assert "applied_ad_filter" in detail_source
    assert "groupby(identity_sources)" in detail_source
    assert "dict(identity_config)" in detail_source
    assert "build_meta_campaign_total_row(" in detail_source
    assert "identity_labels=identity_labels" in detail_source
    assert 'st.markdown(f"### {detail_title}")' in detail_source
    assert 'csv_export_frame["frame"] = campaign_summary' in detail_source
```

- [ ] **Step 8: Run the wiring test and verify RED**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_dashboard_ui.py::test_meta_detail_table_uses_dynamic_identity_columns \
  -v
```

Expected: failure because the table block still hardcodes campaign grouping and
its title.

- [ ] **Step 9: Wire the applied hierarchy into the existing table block**

Import `meta_detail_table_config` from `dashboard.utils`.

Immediately after `df_table = df_curr.copy()`, derive the table configuration:

```python
identity_config = (("base_campaign_name", "Campaña"),)
detail_title = "Detalle de Campañas y Resultados"
if platform_key == "meta_ads":
    identity_config, detail_title = meta_detail_table_config(
        applied_campaign_filter,
        applied_adset_filter,
        applied_ad_filter,
        set(df_table.columns) | {"base_campaign_name"},
    )
identity_sources = [column for column, _ in identity_config]
identity_labels = [label for _, label in identity_config]
st.markdown(f"### {detail_title}")
```

Remove the previous hardcoded section-title call.

Before the first `df_table.groupby(group_keys)`, preserve child dimensions:

```python
for column in identity_sources:
    if column in df_table.columns and column not in group_keys:
        group_keys.append(column)
```

After `meta_table["base_campaign_name"]` is created, replace the hardcoded
`groupby("base_campaign_name")` with:

```python
.groupby(identity_sources)
```

Build the dynamic TOTAL row before formatting:

```python
total_row = build_meta_campaign_total_row(
    campaign_summary,
    identity_labels=identity_labels,
)
```

Select and rename dynamic identity columns with the existing metric columns:

```python
campaign_summary = campaign_summary[
    identity_sources + [
        "result_label",
        "results",
        "cost_per_result",
        "cpm",
        "impressions",
        "clicks",
        "cpc",
        "spend",
    ]
].rename(columns={
    **dict(identity_config),
    "result_label": "Tipo de resultado",
    "results": "Resultados",
    "cost_per_result": "Costo por resultado",
    "cpm": "CPM",
    "impressions": "Impresiones",
    "clicks": "Clics",
    "cpc": "CPC",
    "spend": "Inversión",
})
```

Keep the existing sequence:

```python
campaign_summary = pd.concat(
    [campaign_summary, pd.DataFrame([total_row])],
    ignore_index=True,
)
csv_export_frame["frame"] = campaign_summary
show_theme_table(campaign_summary, merge_total_cells=True)
```

- [ ] **Step 10: Run focused drill-down tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_ui.py \
  -k "meta_detail_table or campaign_total_row" -v
```

Expected: all hierarchy, fallback, TOTAL-row, and wiring tests pass.

- [ ] **Step 11: Run the complete dashboard regression set**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_dashboard_exports.py tests/test_dashboard_ui.py -q
.venv/bin/python -m py_compile dashboard.py dashboard/ui.py dashboard/utils.py
git diff --check
```

Expected: every selected test passes, all files compile, and the diff has no
whitespace errors. The Streamlit `AppTest` cases in
`tests/test_dashboard_ui.py` are the local runtime harness; live Meta API
validation is intentionally excluded because it requires account credentials.

- [ ] **Step 12: Commit the drill-down work unit**

Run:

```bash
git add dashboard.py dashboard/utils.py tests/test_dashboard_ui.py
git commit --no-verify -m "feat(dashboard): drill Meta details into ad sets and ads"
```

Expected: one feature commit. `dashboard/ui.py` and
`tests/test_dashboard_exports.py` should remain unchanged from Task 1.

Rollback boundary: reverting this commit restores campaign-only table grouping
without removing the previously approved TOTAL-row or CSV behavior.

---

### Task 3: Final Verification

**Files:**

- Verify: `dashboard.py`
- Verify: `dashboard/ui.py`
- Verify: `dashboard/utils.py`
- Verify: `tests/test_dashboard_exports.py`
- Verify: `tests/test_dashboard_ui.py`

**Interfaces:**

- Consumes: the baseline and drill-down commits from Tasks 1 and 2.
- Produces: verification evidence only; no additional code.

- [ ] **Step 1: Verify tests and compilation from committed state**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_dashboard_exports.py tests/test_dashboard_ui.py -q
.venv/bin/python -m py_compile dashboard.py dashboard/ui.py dashboard/utils.py
git diff --check
```

Expected: zero test failures, compilation exit code `0`, and no diff-check
findings.

- [ ] **Step 2: Verify commit and working-tree boundaries**

Run:

```bash
git log --oneline -3
git status --short
```

Expected:

- One baseline commit for TOTAL/CSV behavior.
- One feature commit for hierarchical table grouping.
- No uncommitted implementation files.
- No push or deployment.

- [ ] **Step 3: Verify requirements against source**

Confirm:

- No applied filters use campaign identity.
- Applied campaigns use Campaign + Ad set.
- Applied ad sets or a specific ad use Ad set + Ad.
- The table level changes only after **Aplicar filtros**.
- TOTAL remains last and spans the first two cells.
- The deferred CSV frame is assigned after the final table DataFrame is built.
- No backend, connector, KPI, or ranking file changed.
