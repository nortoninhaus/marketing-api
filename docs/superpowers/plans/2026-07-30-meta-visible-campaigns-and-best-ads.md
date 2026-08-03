# Meta Visible Campaigns and Best Ads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Show only delivered Meta campaigns, report unique reach correctly, add spend efficiency to the summary, and display each campaign's best ad for the active ranking metric.

**Architecture:** Keep the existing daily campaign query for additive metrics. Reuse the existing Meta proxy for aggregate account, campaign, and ad insights; isolate the two deterministic dataframe decisions in `dashboard/utils.py`; then wire the results into the existing Streamlit layout.

**Tech Stack:** Python 3.14, pandas, Streamlit, requests, pytest.

## Global Constraints

- Add no dependencies.
- Do not change, push, or deploy the backend.
- Preserve campaign totals and ranking order; only the previewed ad changes.
- Use account-level reach for **Alcance Total**, campaign-level reach for the reach ranking, and ad-level reach for winner selection.

---

### Task 1: Campaign eligibility and metric-specific ad winners

**Files:**
- Modify: `dashboard/utils.py`
- Test: `tests/test_dashboard_ui.py`

**Interfaces:**
- Produces: `meta_campaigns_with_impressions(frame) -> set[str]`
- Produces: `select_meta_ad_winners(ad_rows, ranked_campaigns_by_metric) -> dict[tuple[str, str], dict]`

- [ ] **Step 1: Write failing behavior tests**

Add tests proving:

```python
def test_meta_campaigns_with_impressions_uses_positive_campaign_total():
    frame = pd.DataFrame({
        "campaign_name": ["Delivered_facebook", "Delivered_instagram", "Empty_facebook"],
        "impressions": [0, 12, 0],
    })
    assert dashboard_utils.meta_campaigns_with_impressions(frame) == {"Delivered"}


def test_select_meta_ad_winners_uses_each_ranking_metric():
    rows = [
        {"campaign_name": "Campaign", "ad_id": "2", "impressions": 100, "lead": 9, "reach": 20, "post_engagement": 1},
        {"campaign_name": "Campaign", "ad_id": "1", "impressions": 200, "lead": 2, "reach": 80, "post_engagement": 7},
    ]
    ranked = {"lead": ["Campaign"], "reach": ["Campaign"], "post_engagement": ["Campaign"]}
    winners = dashboard_utils.select_meta_ad_winners(rows, ranked)
    assert winners[("lead", "Campaign")]["ad_id"] == "2"
    assert winners[("reach", "Campaign")]["ad_id"] == "1"
    assert winners[("post_engagement", "Campaign")]["ad_id"] == "1"
```

- [ ] **Step 2: Verify the tests fail for missing behavior**

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_ui.py \
  -k "meta_campaigns_with_impressions or select_meta_ad_winners" -v
```

Expected: both tests fail because the helpers do not exist.

- [ ] **Step 3: Implement the minimum dataframe helpers**

- Normalize campaign names with the existing `meta_base_campaign_name`.
- Sum impressions by normalized name and return only positive totals.
- Select one ad per `(metric, campaign)` by metric descending, impressions descending, and ad ID ascending.
- Return no winner when a campaign has no ad insight row.

- [ ] **Step 4: Verify the focused tests pass**

Run the Step 2 command.

Expected: 2 passed.

---

### Task 2: Aggregate Meta Insights and targeted previews

**Files:**
- Modify: `dashboard/api.py`
- Test: `tests/test_dashboard_ui.py`

**Interfaces:**
- Produces: `fetch_meta_aggregate_insights(client_id, account_id, start_date, end_date, level, api_filters, api_key) -> tuple[list[dict], str | None]`
- Replaces: `fetch_meta_campaign_previews(...)` with `fetch_meta_ad_previews(client_id, account_id, preview_targets, api_key) -> tuple[list[dict], str | None]`
- `preview_targets` contains `(ranking_metric, campaign_name, ad_id, ad_name)` tuples.

- [ ] **Step 1: Write failing API tests**

Monkeypatch `dashboard.api.requests.post` and prove:

- account insights preserve the single aggregate reach value;
- campaign/ad pagination follows `paging.cursors.after`;
- ad actions normalize `lead` and `post_engagement`;
- targeted previews return `ranking_metric`, `campaign_name`, and the requested `ad_id`.

- [ ] **Step 2: Verify API tests fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_ui.py \
  -k "meta_aggregate_insights or targeted_meta_ad_previews" -v
```

Expected: failures because the new API functions do not exist.

- [ ] **Step 3: Implement aggregate insight loading**

- Call `act_<account>/insights` through the existing `/api/v1/meta-proxy`.
- Send `time_range`, `level`, `fields`, translated Graph `filtering`, and `limit=500`.
- Do not send `time_increment` or breakdowns.
- Follow cursors until no unseen `after` value remains.
- Normalize numeric fields and supported Meta action types.
- Return an error string rather than raising into the Streamlit render.

- [ ] **Step 4: Implement previews for explicit winning ad IDs**

- Fetch each unique winning ad by ID rather than scanning the account and choosing the first ad.
- Reuse the existing preview and effective-story hydration behavior.
- Preserve one result per `(ranking_metric, campaign_name)`.

- [ ] **Step 5: Verify the focused API tests pass**

Run the Step 2 command.

Expected: all selected tests pass.

---

### Task 3: Wire visibility, summary metrics, reach, and previews

**Files:**
- Modify: `dashboard.py`
- Test: `tests/test_dashboard_ui.py`

**Interfaces:**
- Consumes: both helpers from Task 1.
- Consumes: both Meta API functions from Task 2.

- [ ] **Step 1: Write failing dashboard wiring assertions**

Add assertions proving the dashboard:

- filters current and previous Meta frames through `meta_campaigns_with_impressions`;
- builds the campaign selector from the already-filtered frame;
- uses account aggregate reach for **Alcance Total**;
- renders **Costo por resultado** as `total_spend / curr_primary` and renders **Importe gastado** beside the lead summary;
- replaces campaign reach in rankings with campaign aggregate insight values;
- selects and keys previews by `(metric, base_campaign_name)`.

- [ ] **Step 2: Verify wiring tests fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_ui.py \
  -k "delivered_meta_campaigns or aggregate_meta_reach or lead_summary_cost or metric_specific_preview" -v
```

Expected: failures because the dashboard still uses unfiltered frames, summed reach, and campaign-only previews.

- [ ] **Step 3: Apply the eligible campaign set once**

- Immediately after normalizing required columns, filter Meta current and previous frames to campaigns with positive aggregate impressions.
- Let the existing selector, detail table, featured table, KPI calculations, and rankings consume those filtered frames.

- [ ] **Step 4: Load and use aggregate insights**

- Cache the three level queries by account, period, and active API filters.
- Use account reach for the total card.
- Map campaign reach into campaign ranking rows before sorting.
- Use ad insights only to choose winners; do not replace campaign totals.
- Render `—` when account aggregate reach fails instead of falling back to summed daily reach.

- [ ] **Step 5: Update the summary and previews**

- Render leads, cost per result, and spend in the summary card.
- Build preview targets from metric-specific winners.
- Key preview lookup by `(ranking metric, campaign name)`.

- [ ] **Step 6: Verify focused and regression tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_ui.py -v
.venv/bin/python -m pytest tests/test_meta.py -v
.venv/bin/python -m py_compile dashboard.py dashboard/api.py dashboard/utils.py
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit the work unit**

```bash
git add dashboard.py dashboard/api.py dashboard/utils.py tests/test_dashboard_ui.py
git commit -m "fix(dashboard): correct Meta reach and ranked ad previews"
```

Runtime verification: local Streamlit smoke test if credentials are available; otherwise the proxy boundary is covered by mocked responses and compilation.

Rollback boundary: revert this implementation commit to restore the prior campaign filtering, reach calculation, summary, and preview selection without touching the two design commits.
