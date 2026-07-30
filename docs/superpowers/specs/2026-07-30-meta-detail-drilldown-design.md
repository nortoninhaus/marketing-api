# Meta Detail Table Drill-Down Design

## Goal

Make the Meta Ads detail table follow the applied filter hierarchy without
requesting additional backend data:

- No applied campaign filter: show campaigns.
- Applied campaign filter: show each selected campaign's ad sets.
- Applied ad-set filter: show the ads from each selected ad set.

The table must preserve parent context, its current metrics and TOTAL row, and
CSV parity.

## Current Behavior

The filters already cascade from Campaign to Ad set to Ad, and the detail query
already requests `adset_name` and `ad_name`. After the filters are applied,
`df_curr` contains the necessary child-level rows.

The detail table still groups the filtered rows back into
`base_campaign_name`, which discards the ad-set and ad breakdown. This is a
presentation-layer grouping problem, not a backend or API problem.

## Applied Filter Behavior

The table level is derived only from applied session-state filters. Changing a
widget does not affect the table until the user presses **Aplicar filtros**.

| Applied state | Identity columns | Section title |
| --- | --- | --- |
| No campaign, ad set, or ad | `Campaña` | `Detalle de Campañas y Resultados` |
| One or more campaigns, no ad set or ad | `Campaña`, `Conjunto de anuncios` | `Detalle de Conjuntos de anuncios y Resultados` |
| One or more ad sets, or a specific ad | `Conjunto de anuncios`, `Anuncio` | `Detalle de Anuncios y Resultados` |

An applied ad filter keeps the table at ad level even when the user selected
the ad directly without first selecting an ad set.

## Data Flow

1. Keep the current cascading filter widgets and **Aplicar filtros** button.
2. Keep requesting `adset_name` and `ad_name` in the existing Meta detail
   query.
3. Apply campaign, ad-set, and ad filters to `df_curr` as today.
4. Select the table identity columns from the applied filter state.
5. Add those identity columns to the existing aggregation keys.
6. Reuse the current result-indicator selection, metric aggregation, sorting,
   formatting, and TOTAL-row calculations.
7. Assign the final displayed DataFrame to the deferred CSV export holder.
8. Render that same DataFrame.

No duplicate aggregation path or additional API request is introduced.

## Metrics and Totals

Every drill-down level keeps the current metric columns:

- Tipo de resultado
- Resultados
- Costo por resultado
- CPM
- Impresiones
- Clics
- CPC
- Inversión

Rows remain sorted by Resultados in descending order.

The TOTAL row keeps the currently approved rules:

- `Resultados`: sum.
- `Costo por resultado`: arithmetic mean of displayed row values.
- `CPM`: total spend multiplied by 1,000 and divided by total impressions.
- `Impresiones`: sum.
- `Clics`: sum.
- `CPC`: total spend divided by total clicks.
- `Inversión`: sum.
- `Tipo de resultado`: blank.

`TOTAL` occupies the first two table cells. At campaign level those cells are
Campaña and Tipo de resultado. At child levels they are the two identity
columns, while Tipo de resultado remains blank.

## CSV Export

The Meta CSV must serialize the exact final DataFrame rendered by the table:

- Same drill-down level.
- Same identity and metric columns.
- Same ordering and formatting.
- Same TOTAL row.

Other platform exports retain their current behavior.

## Error Handling

The existing empty-data handling remains unchanged. The drill-down introduces
no new remote failure mode because it uses dimensions already returned by the
detail query. A missing child-level column falls back to the campaign-level
identity instead of raising a grouping `KeyError`.

## Testing

Automated tests must cover:

1. No applied hierarchy filters produces campaign rows.
2. Applied campaigns produce Campaign + Ad set rows.
3. Applied ad sets produce Ad set + Ad rows.
4. A directly applied ad also uses the ad-level schema.
5. Multiple parents remain distinguishable through the parent column.
6. Existing metric and TOTAL-row calculations remain unchanged.
7. The CSV uses the exact displayed drill-down DataFrame.

## Out of Scope

- Automatic filter application.
- Expandable or nested table rows.
- Changes to KPI cards or rankings.
- Backend or Meta connector changes.
- Push or deployment.
