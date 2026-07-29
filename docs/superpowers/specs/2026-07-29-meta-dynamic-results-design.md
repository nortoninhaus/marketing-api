# Show Meta campaign results with official labels

Expose the result indicator selected by Meta together with its matching value and cost. The dashboard will use Meta's official Spanish terminology, remove the duplicated reach column, and rank campaign cards by leads.

## Decision

Keep the raw result selection in the Meta connector and the Spanish presentation in the dashboard:

- The backend returns `result_indicator`, `results`, and `cost_per_result`.
- Meta's explicit `results` and `cost_per_result` pair takes precedence.
- When that pair is absent, the connector selects the matching action and cost using the campaign objective or optimization goal.
- The dashboard translates known indicators through an explicit catalog of official Meta labels.
- Unknown indicators display `—`; the dashboard does not invent or humanize labels.

## Data flow

1. Request Meta result, action, cost, objective, and optimization data needed for the selected campaign rows.
2. Resolve one indicator and its corresponding value and cost for each row.
3. Preserve `result_indicator` while normalizing the API response into the dashboard data frame.
4. Aggregate campaign results without mixing different indicators.
5. Render the official result label beside its value and cost.

## Dashboard changes

- **Desempeño de campañas destacadas**
  - Show every campaign.
  - Preserve the complete campaign name.
  - Remove **Reach** because it duplicates **Resultados** for reach campaigns.
  - Show **Tipo de resultado**, **Resultados**, **Costo por resultado**, **CPM**, **Impresiones**, **Clics**, **CPC**, and **Inversión**.
- **Ranking: top campañas por clientes potenciales (Meta)**
  - Sort descending by leads.
  - Keep the top eight cards.
  - Add **Clientes potenciales** to every card.
- Increment the dashboard cache version so cached frames cannot hide the new schema.

## Failure handling

- Missing values or costs remain zero without breaking aggregation.
- A missing official translation renders `—`.
- Campaigns with zero leads remain visible in the full table but rank after campaigns with leads.

## Verification

- Connector tests cover an explicit Meta result pair and an action-based lead fallback.
- Dashboard API tests verify that the indicator survives normalization.
- Dashboard UI tests verify official labels, full campaign names, all-campaign display, removal of Reach, and lead ordering/cards.
- Run focused tests first, then the complete relevant test files.

## Delivery

- Keep dashboard changes local; do not push or deploy them.
- Deploy the backend with `deploy.sh` only if backend files change.
- Do not add dependencies or unrelated refactors.
