# Show three Meta campaign rankings

Replace the single Meta campaign ranking with three independent top-three rankings for leads, reach, and interactions. Keep campaign-level aggregation and reuse the current preview card.

## Ranking behavior

| Ranking | Sort metric | First card metric |
|---|---|---|
| Clientes potenciales | `lead` descending | Clientes potenciales |
| Alcance | `reach` descending | Alcance |
| Interacciones | `post_engagement` descending | Interacciones |

- Show exactly the top three campaigns available in each ranking.
- Keep full campaign names and the current campaign preview behavior.
- A campaign may appear in more than one ranking.
- Keep the remaining card metrics after the ranking metric without duplicating it.

## Data flow

1. Request `post_engagement` as a standard Meta Ads metric alongside `lead` and `reach`.
2. Parse it from Meta's `actions` payload using the connector's existing custom-action handling.
3. Aggregate each ranking metric by base campaign name across publisher platforms.
4. Build the union of ranked campaign names and fetch previews once for that deduplicated set.
5. Render the three rankings with the existing card template.

## Backend

- Add `post_engagement` to the Meta Ads schema so the dashboard can request it.
- Do not introduce a new endpoint or dependency.
- Preserve the existing zero fallback when Meta omits the action.

## Dashboard

- Render three stacked sections with three columns each.
- Move the active ranking metric to the first metric row in every card.
- Preserve preview errors and the existing “Preview no disponible” fallback.
- Keep dashboard changes local; deploy only the backend if its change is required.

## Verification

- Connector test: `post_engagement` is exposed and parsed from `actions`.
- Dashboard test: the three headings exist, each ranking uses its own descending metric and `.head(3)`, and its metric appears first.
- Run the focused Meta connector and dashboard test suites.

## Out of scope

- Ranking individual ads or posts.
- Changing campaign filters, featured campaign performance, or hashtag rankings.
- Adding pagination for more preview candidates.
