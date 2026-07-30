# Correct Meta campaign totals and ranked ad previews

Keep campaign-level rankings and metrics, but only show delivered campaigns and attach the best ad for each ranking metric.

## Decisions

| Area | Decision |
|---|---|
| Campaign eligibility | A campaign is visible when its current-period impressions, grouped by base campaign name, are greater than zero. |
| Filter timing | Determine eligibility after the insights response because impressions are returned metrics, not pre-query filter values. |
| Reach | Load aggregate Meta Insights without daily or publisher-platform breakdowns: account level for **Alcance Total** and campaign level for the reach ranking. |
| Summary | Show **Clientes Potenciales**, **Costo por resultado**, and **Importe gastado** together. Cost per result is total spend divided by total leads. |
| Ranking cards | Preserve campaign totals and ranking order. Change only the displayed ad to the highest-performing ad inside that campaign for the section metric. |
| Backend | Reuse the existing Meta proxy; do not add an endpoint or dependency. |

## Data flow

1. Load the current campaign data as today.
2. Group impressions by normalized base campaign name and retain names whose total is greater than zero.
3. Use that eligible set for the campaign selector, detail table, featured campaigns, and all three rankings.
4. Query Meta Insights through the existing proxy at account level, without `time_increment` or breakdowns, to obtain the unique total reach for the active date range and filters.
5. Query Meta Insights at campaign level for the reach ranking without reconstructing campaign reach from daily rows.
6. Query Meta Insights once at ad level for the same period and active filters.
7. For every ranked campaign, select its winning ad independently:
   - leads ranking: highest ad `lead`;
   - reach ranking: highest aggregate ad `reach`;
   - interaction ranking: highest ad `post_engagement`.
8. Fetch and render previews only for those winning ad IDs. If one campaign wins multiple sections with different ads, each section shows its own winner.

## Aggregation rules

- Impressions, spend, leads, clicks, conversions, and post engagement remain additive.
- **Alcance Total** comes from the account-level aggregate row. Campaign reach comes from campaign-level aggregate rows.
- Never calculate total reach by summing dates, platforms, or campaigns because the same user can exist in more than one group.
- Ranking values and all secondary card metrics remain campaign totals.
- Ties between ads are resolved by impressions descending, then ad ID ascending for deterministic output.
- When leads are zero, cost per result is `$0.00`.

## Failure handling

- If aggregate reach cannot be loaded, show `—` instead of the known-wrong summed value.
- If ad-level metrics or a preview cannot be loaded, keep the campaign card and render the existing preview-unavailable state.
- Campaigns with zero or missing impressions do not appear.

## Verification

- A focused test proves zero-impression campaigns are absent from selector, table, featured campaigns, and rankings.
- A focused test proves total reach uses the account aggregate and campaign rankings use campaign aggregates rather than sums of daily rows.
- A focused test proves summary cost per result is `spend / lead` and includes total spend.
- A focused test proves each ranking selects the best ad by its own metric while retaining campaign totals.
- Run the focused dashboard tests and the relevant Meta connector tests.

## Constraints

- Add no dependencies.
- Keep changes local; do not push or deploy.
- Avoid unrelated dashboard refactors.
