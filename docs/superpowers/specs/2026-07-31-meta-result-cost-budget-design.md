# Native Meta Result Cost and Budget Design

## Decision

Reuse the existing Meta Proxy from the dashboard. The detail table will use
Meta's native period-level **Cost per result**, add budget metadata at the level
that owns it, rename **Inversión** to **Importe gastado**, and keep the rendered
table and CSV identical.

No backend, connector, push, or deployment change is required.

## Current Problem

The main campaign query returns daily rows split by publisher platform. The
table currently recalculates Cost per result as:

```text
sum(daily results × daily native cost) / sum(daily results)
```

That calculation does not reproduce Meta Ads Manager, especially for
non-additive result types such as Reach. Budget is also absent because it is
campaign/ad-set metadata, not an Insights metric.

## Data Sources

### Native period result cost

Extend the existing cached aggregate Insights request in `dashboard/api.py`:

- Query the active table level: campaign, ad set, or ad.
- Use the selected date range without `time_increment` or publisher breakdowns.
- Request `results`, `cost_per_result`, result-resolution fields, and stable
  entity IDs/names.
- Apply the currently applied campaign/ad-set/ad filters.
- Match each result's `indicator` to the corresponding native cost entry.

The detail table merges this period-level value into its rows. It must not
derive or reweight Cost per result from the daily reporting DataFrame. If Meta
does not return a native value for a row, display `N/D` rather than fabricate a
number.

The TOTAL row keeps the approved arithmetic mean of available displayed native
cost values.

### Budget metadata

Extend the existing `fetch_meta_filter_rows()` ads query. Its nested campaign
and ad-set objects will request:

- `id`
- `name`
- `daily_budget`
- `lifetime_budget`

Meta budget values are normalized from minor currency units before display.
This reuses the request already needed for the hierarchical filters; it does
not introduce a second budget API path.

## Budget Display Rules

| Table level | Entity state | Presupuesto |
| --- | --- | --- |
| Campaign | Has lifetime budget | Formatted total amount |
| Campaign | Has only daily budget | `Presupuesto diario` |
| Campaign | Has neither | `Se administra a nivel de conjuntos` |
| Ad set | Has lifetime budget | Formatted total amount |
| Ad set | Has only daily budget | `Presupuesto diario` |
| Ad set | Has neither | `Se administra a nivel campaña` |
| Ad | Parent ad set owns budget | `Se administra a nivel de conjuntos` |
| Ad | Campaign owns budget | `Se administra a nivel campaña` |

Ad rows never repeat a parent amount. Campaign rows never sum ad-set budgets,
and ad-set rows never copy campaign budgets.

The TOTAL row sums only numeric lifetime-budget values displayed at the active
level. Text states do not contribute to the total.

## Table and CSV

The final metric order is:

1. Existing identity columns for the active drill-down level.
2. Tipo de resultado.
3. Resultados.
4. Costo por resultado.
5. CPM.
6. Impresiones.
7. Clics.
8. CPC.
9. Presupuesto.
10. Importe gastado.

`Inversión` is renamed only in this Meta detail table and its CSV. The deferred
CSV export continues to serialize the exact final DataFrame rendered on screen,
including the TOTAL row and mixed text/currency budget column.

## Data Flow

1. Keep the existing filter widgets and explicit **Aplicar filtros** button.
2. Reuse filter metadata to determine campaign/ad-set budget ownership.
3. Derive the active table level from the applied filters as today.
4. Reuse the existing aggregate Insights call for campaign and ad levels; make
   the equivalent ad-set call only when the table is at ad-set level.
5. Merge native aggregate Cost per result and budget metadata into the current
   grouped table rows.
6. Build the TOTAL row from unformatted numeric source columns.
7. Format and order columns once.
8. Assign that exact DataFrame to the CSV holder and render it.

## Error Handling

- Aggregate native result cost unavailable: show `N/D` for the affected row.
- Budget metadata request unavailable: show `N/D`; do not guess ownership.
- A valid metadata response with no budget at the current level follows the
  ownership text rules above.
- Existing empty-data and missing-child-column behavior remains unchanged.

## Testing

Automated tests will cover:

1. Aggregate Insights requests native result and cost fields at the active level.
2. The cost parser matches the result indicator and never reweights daily rows.
3. Campaign, ad-set, and ad budget display rules.
4. Minor-unit normalization for numeric lifetime budgets.
5. TOTAL sums only numeric budgets and averages available native costs.
6. Column order ends with `Presupuesto`, `Importe gastado`.
7. CSV receives the same final DataFrame rendered by the table.
8. Existing drill-down and light-theme sidebar regressions remain green.

## Out of Scope

- Displaying the numeric daily-budget amount.
- Summing budgets owned by child entities into a parent row.
- Repeating parent budget amounts on ad rows.
- Changes to KPI cards, rankings, backend connectors, or API schemas.
- Push or deployment.
