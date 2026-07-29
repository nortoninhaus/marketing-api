# Meta Campaign Aggregation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Present each Meta campaign once, support 0..N ad-set filters, and hide empty hashtag sections.

**Architecture:** Keep publisher-platform rows in the fetched DataFrame. Deduplicate campaign choices and aggregate only at the dashboard presentation boundary.

**Tech Stack:** Python, pandas, Streamlit, pytest.

## Global Constraints

- Dashboard only; no backend change or deployment.
- Keep `publisher_platform` in API requests.
- No dependencies.

### Task 1: Multi-value filters

**Files:** `dashboard.py`, `dashboard/utils.py`, `tests/test_dashboard_ui.py`

- [ ] Add failing tests for unique base campaign options, ad-set multiselect, and list-based DataFrame filtering.
- [ ] Run focused tests and verify failure.
- [ ] Build campaign options from unique `meta_base_campaign_name` values.
- [ ] Replace the ad-set selectbox with a multiselect whose empty value means no filter.
- [ ] Update API/detail filters and `apply_dashboard_filters` to accept all selected ad sets.
- [ ] Run focused tests and verify success.

### Task 2: One featured row per campaign

**Files:** `dashboard.py`, `tests/test_dashboard_ui.py`

- [ ] Add failing assertions requiring campaign-only grouping and no Platform column.
- [ ] Run focused tests and verify failure.
- [ ] Sort source rows by results, then group only by base campaign name so the greatest-result non-empty indicator becomes the single result type.
- [ ] Sum metrics across publisher platforms and retain weighted cost per result.
- [ ] Run focused tests and verify success.

### Task 3: Silent empty hashtags and verification

**Files:** `dashboard.py`, `tests/test_dashboard_ui.py`

- [ ] Add a failing assertion that the empty hashtag caption is absent.
- [ ] Remove both empty hashtag branches and initialize the ads hashtag list before conditional preview rendering.
- [ ] Run `PYTHONPATH=. .venv/bin/pytest tests/test_dashboard_ui.py -q`.
- [ ] Run Python compilation and `git diff --check`.
- [ ] Commit locally without the external review hook.
