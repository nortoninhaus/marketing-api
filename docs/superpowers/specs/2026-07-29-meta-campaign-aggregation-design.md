# Unify Meta campaign reporting

Keep publisher-platform data internally, but present one campaign option and one featured-table row per Meta campaign.

## Filters

- Build **Campañas** options from unique base campaign names, without Facebook or Instagram suffixes.
- Change **Conjunto de anuncios** to **Conjuntos de anuncios** with a multiselect accepting zero to many values.
- An empty ad-set selection means no ad-set filter.
- Selected ad sets produce one API filter containing every matching ad-set ID.
- Keep the single-ad selector scoped to the selected campaigns and ad sets.

## Featured campaigns

- Group by base campaign name only.
- Remove **Plataforma**.
- Sum results, impressions, clicks, and spend across publisher platforms.
- Preserve one result type by selecting the non-empty indicator from the row with the greatest result count.
- Keep cost per result weighted by result volume.

## Hashtags

- Render a hashtag ranking only when hashtags exist.
- Render no heading, table, caption, or placeholder when none exist.

## Constraints

- Do not remove the `publisher_platform` API breakdown.
- Do not change the backend.
- Keep dashboard changes local.
- Add no dependencies.
