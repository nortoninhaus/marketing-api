# Campaign Table Total Row Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Append one mathematically correct TOTAL row to the Meta campaign performance table.

**Architecture:** Put the aggregation and formatting rules in one pure dashboard utility, test it directly, and append its result after existing campaign rows are formatted and renamed.

**Tech Stack:** Python 3.14, pandas, Streamlit, pytest.

## Global Constraints

- Dashboard only; no backend or dependency changes.
- Keep the total row last.
- Never arithmetic-average CPM, CPC, or cost per result.

---

### Task 1: Calculate and render the total row

**Files:**
- Modify: `dashboard/utils.py`
- Modify: `dashboard.py`
- Test: `tests/test_dashboard_ui.py`

**Interfaces:**
- Produces: `build_meta_campaign_total_row(frame) -> dict`
- Consumes the unformatted campaign summary columns already built in `dashboard.py`.

- [ ] **Step 1: Write failing utility tests**

Add one test with a common result type and one with mixed types. Verify:

```python
row = dashboard_utils.build_meta_campaign_total_row(frame)
assert row["Campaña"] == "TOTAL"
assert row["Resultados"] == "40"
assert row["Costo por resultado"] == "$3.50"
assert row["CPM"] == "$20.00"
assert row["CPC"] == "$0.40"
assert row["Inversión"] == "$200.00"
```

For mixed result indicators, verify `Tipo de resultado == "Resultados mixtos"` and both `Resultados` and `Costo por resultado` equal `—`.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_ui.py -k "campaign_total_row" -v
```

Expected: failure because `build_meta_campaign_total_row` does not exist.

- [ ] **Step 3: Implement the minimum utility**

- Sum spend, impressions, clicks, results, and result-weighted cost.
- Recalculate CPM and CPC from aggregate values.
- Use the common official result label only when exactly one result indicator exists.
- Return already formatted display values.

- [ ] **Step 4: Append the row after campaign formatting**

Call the utility before numeric columns are converted to strings, then append its returned dictionary after rename/sort with `pd.concat(..., ignore_index=True)`.

- [ ] **Step 5: Verify focused and regression tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_dashboard_ui.py -q
.venv/bin/python -m py_compile dashboard.py dashboard/utils.py
```

Expected: all commands exit 0.

- [ ] **Step 6: Commit**

```bash
git add dashboard.py dashboard/utils.py tests/test_dashboard_ui.py
git commit -m "feat(dashboard): add campaign table total row"
```

Rollback boundary: revert the implementation commit to remove only the total-row calculation and rendering.
