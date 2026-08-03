# Add a correct total row to campaign performance

Append one **TOTAL** row to the Meta campaign performance table without averaging incompatible rates.

## Aggregation rules

| Column | Total-row behavior |
|---|---|
| Campaña | `TOTAL` |
| Tipo de resultado | Keep the common official label; otherwise `Resultados mixtos` |
| Resultados | Sum only when every campaign has the same result type; otherwise `—` |
| Costo por resultado | Result-weighted average when the result type is common; otherwise `—` |
| CPM | `total spend × 1000 / total impressions` |
| Impresiones | Sum |
| Clics | Sum |
| CPC | `total spend / total clicks` |
| Inversión | Sum |

## Rendering

- Calculate totals before formatting campaign values as strings.
- Append the formatted row after campaign sorting so it always remains last.
- Use `$0.00` for rate divisions with a zero denominator.

## Verification

- Test one common result type with totals and weighted/recalculated rates.
- Test mixed result types display `Resultados mixtos` and `—` for incompatible fields.
- Run dashboard UI tests and Python compilation.

## Constraints

- Dashboard-only change.
- Add no dependencies.
- Keep work local on `fixed-cards`; do not push or deploy.
