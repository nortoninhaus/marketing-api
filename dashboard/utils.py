import re
import calendar
from datetime import date
import pandas as pd
from dashboard.config import DIMENSION_VALUE_LABELS, META_RESULT_LABELS

# Helper function to extract metrics robustly
def extract_metric(metrics, keys):
    for key in keys:
        if key in metrics and metrics[key] is not None:
            try:
                return float(metrics[key])
            except ValueError:
                pass
    return 0.0


def translate_dimension_value(column, value):
    if value is None:
        return "Desconocido"
    text = str(value)
    return DIMENSION_VALUE_LABELS.get(column, {}).get(text.lower(), text)


def translate_meta_result_indicator(value):
    return META_RESULT_LABELS.get(str(value or "").lower(), "—")


def clean_region_name(value):
    return re.sub(r"\s+Province$", "", str(value)).replace("Province", "Provincia").strip()


def clean_campaign_name(value):
    text = re.sub(r"[_/|-]+", " ", str(value))
    text = re.sub(r"\b(normal|mundial|automatico|autom[aá]tico|fb|ig|facebook|instagram|interaccion|interacción|alcance|impresiones)\b", " ", text, flags=re.I)
    text = re.sub(r"\b\d{1,2}[.-]\d{1,2}[.-]\d{2,4}\b|\b20\d{2}\b", " ", text)
    return re.sub(r"\s+", " ", text).strip().title() or str(value)


def meta_base_campaign_name(value):
    return re.sub(r"_(facebook|instagram|audience_network|messenger|whatsapp|unknown|threads)$", "", str(value), flags=re.I)


def meta_campaigns_with_impressions(frame):
    if frame.empty or not {"campaign_name", "impressions"}.issubset(frame.columns):
        return set()

    totals = pd.to_numeric(frame["impressions"], errors="coerce").fillna(0).groupby(
        frame["campaign_name"].map(meta_base_campaign_name)
    ).sum()
    return set(totals[totals > 0].index)


def select_meta_ad_winners(ad_rows, ranked_campaigns_by_metric):
    winners = {}
    for metric, campaign_names in ranked_campaigns_by_metric.items():
        for campaign_name in campaign_names:
            candidates = [
                row
                for row in ad_rows
                if meta_base_campaign_name(row.get("campaign_name", "")) == campaign_name
            ]
            if candidates:
                winners[(metric, campaign_name)] = min(
                    candidates,
                    key=lambda row: (
                        -extract_metric(row, [metric]),
                        -extract_metric(row, ["impressions"]),
                        str(row.get("ad_id") or ""),
                    ),
                )
    return winners


def select_meta_top_ads(ad_rows, metrics, limit=3):
    tops = {}
    for metric in metrics:
        ranked = sorted(
            (row for row in ad_rows if row.get("ad_id")),
            key=lambda row: (
                -extract_metric(row, [metric]),
                -extract_metric(row, ["impressions"]),
                str(row.get("ad_id")),
            ),
        )
        unique = {}
        for row in ranked:
            unique.setdefault(str(row["ad_id"]), row)
        tops[metric] = list(unique.values())[:limit]
    return tops


def fetch_meta_detail_rows(
    fetch_data,
    platform_key,
    client_id,
    user_id,
    account_id,
    start_date,
    end_date,
    prev_start_date,
    prev_end_date,
    request_metrics,
    request_dimensions,
    opt_filters,
    adset_filter,
    ad_filter,
    filtered_meta_rows,
    filtered_ad_rows,
    api_key,
):
    dimensions = list(request_dimensions)
    for dimension in ("adset_name", "ad_name"):
        if dimension not in dimensions:
            dimensions.append(dimension)

    filters = {}
    if ad_filter != "Todos" and not filtered_ad_rows.empty:
        filters["ad.id"] = filtered_ad_rows[
            filtered_ad_rows["ad_name"] == ad_filter
        ]["ad_id"].dropna().astype(str).tolist()
    elif adset_filter and not filtered_meta_rows.empty:
        filters["adset.id"] = filtered_meta_rows[
            filtered_meta_rows["adset_name"].isin(adset_filter)
        ]["adset_id"].dropna().astype(str).unique().tolist()

    detail_filters = dict(opt_filters)
    if filters:
        detail_filters["filters"] = filters
    metrics = request_metrics or [
        "impressions", "clicks", "spend", "conversions", "reach", "__results__"
    ]
    current_rows = fetch_data(
        platform_key, client_id, user_id, account_id,
        start_date, end_date, metrics, dimensions, detail_filters, False, api_key,
    )
    previous_rows = fetch_data(
        platform_key, client_id, user_id, account_id,
        prev_start_date, prev_end_date, metrics, dimensions, detail_filters,
        False, api_key, show_errors=False,
    )
    return current_rows, previous_rows


def meta_detail_table_config(
    campaign_filter,
    adset_filter,
    ad_filter,
    available_columns,
):
    campaign_config = (
        (("base_campaign_name", "Campaña"),),
        "Detalle de Campañas y Resultados",
    )
    if adset_filter or ad_filter != "Todos":
        identity_columns = (
            ("adset_name", "Conjunto de anuncios"),
            ("ad_name", "Anuncio"),
        )
        title = "Detalle de Anuncios y Resultados"
    elif campaign_filter:
        identity_columns = (
            ("base_campaign_name", "Campaña"),
            ("adset_name", "Conjunto de anuncios"),
        )
        title = "Detalle de Conjuntos de anuncios y Resultados"
    else:
        return campaign_config

    if not all(column in available_columns for column, _ in identity_columns):
        return campaign_config
    return identity_columns, title


def meta_budget_display(level, metadata):
    if metadata is None:
        return "N/D", 0.0

    campaign_lifetime = float(metadata.get("campaign_lifetime_budget") or 0)
    campaign_daily = float(metadata.get("campaign_daily_budget") or 0)
    adset_lifetime = float(metadata.get("adset_lifetime_budget") or 0)
    adset_daily = float(metadata.get("adset_daily_budget") or 0)

    if level == "campaign":
        if campaign_lifetime > 0:
            return f"${campaign_lifetime:,.2f}", campaign_lifetime
        if campaign_daily > 0:
            return "Presupuesto diario", 0.0
        return "Se administra a nivel de conjuntos", 0.0

    if level == "adset":
        if adset_lifetime > 0:
            return f"${adset_lifetime:,.2f}", adset_lifetime
        if adset_daily > 0:
            return "Presupuesto diario", 0.0
        return "Se administra a nivel campaña", 0.0

    if adset_lifetime > 0 or adset_daily > 0:
        return "Se administra a nivel de conjuntos", 0.0
    return "Se administra a nivel campaña", 0.0


def enrich_meta_campaign_summary(frame, aggregate_rows, filter_rows, level):
    field_pairs = {
        "campaign": (("base_campaign_name", "campaign_name"),),
        "adset": (
            ("base_campaign_name", "campaign_name"),
            ("adset_name", "adset_name"),
        ),
        "ad": (("adset_name", "adset_name"), ("ad_name", "ad_name")),
    }[level]
    id_field = {
        "campaign": "campaign_id",
        "adset": "adset_id",
        "ad": "ad_id",
    }[level]
    known_campaigns = {
        str(row.get("campaign_name"))
        for row in aggregate_rows + filter_rows
        if row.get("campaign_name")
    }

    def canonical_campaign(value):
        value = str(value)
        if value in known_campaigns:
            return value
        matches = sorted(
            (
                name for name in known_campaigns
                if value.startswith(f"{name}_")
                or name.startswith(f"{value}_")
                or meta_base_campaign_name(name) == value
            ),
            key=len,
            reverse=True,
        )
        if not matches or (len(matches) > 1 and len(matches[0]) == len(matches[1])):
            return None
        return matches[0]

    def record_key(record, summary_side):
        values = []
        for summary_field, meta_field in field_pairs:
            field = summary_field if summary_side else meta_field
            value = record.get(field, "")
            if summary_side and meta_field == "campaign_name":
                value = canonical_campaign(value)
                if value is None:
                    return None
            values.append(str(value))
        return tuple(values)

    def record_id(record):
        return str(record.get(id_field) or "")

    def index_values(rows, value_for_row):
        by_key = {}
        by_id = {}
        for row in rows:
            identity = record_id(row)
            value = value_for_row(row)
            by_key.setdefault(record_key(row, False), []).append((identity, value))
            if identity:
                by_id.setdefault(identity, set()).add(value)
        return by_key, by_id

    def source_value(matches, by_id, stable_id, unavailable):
        values = by_id.get(stable_id, set()) if stable_id else set()
        if not values and len(matches) == 1 and not matches[0][0]:
            values = {matches[0][1]}
        return next(iter(values)) if len(values) == 1 else unavailable

    native_by_key, native_by_id = index_values(
        aggregate_rows, lambda row: row.get("cost_per_result")
    )
    native_metric_indexes = {
        metric: index_values(aggregate_rows, lambda row, key=metric: row.get(key))
        for metric in ("results", "spend", "impressions", "clicks")
    }
    budget_by_key, budget_by_id = index_values(
        filter_rows, lambda row: meta_budget_display(level, row)
    )

    result = frame.copy()
    keys = [record_key(row, True) for _, row in result.iterrows()]
    costs = []
    budget_values = []
    for idx, key in enumerate(keys):
        native_matches = native_by_key.get(key, []) if key is not None else []
        budget_matches = budget_by_key.get(key, []) if key is not None else []
        native_ids = {identity for identity, _ in native_matches if identity}
        budget_ids = {identity for identity, _ in budget_matches if identity}
        ambiguous = len(native_ids) > 1 or (
            not native_ids and len(budget_ids) > 1
        )
        stable_id = next(iter(native_ids or budget_ids), None) if not ambiguous else None
        if not ambiguous:
            for metric, (metric_by_key, metric_by_id) in native_metric_indexes.items():
                metric_val = source_value(
                    metric_by_key.get(key, []) if key is not None else [],
                    metric_by_id,
                    stable_id,
                    None,
                )
                if metric_val is not None and not pd.isna(metric_val):
                    result.at[result.index[idx], metric] = metric_val

        cost_val = None
        if not ambiguous:
            cost_val = source_value(
                native_matches,
                native_by_id,
                stable_id,
                None,
            )

        if cost_val is None or (isinstance(cost_val, (int, float)) and pd.isna(cost_val)):
            row_data = result.iloc[idx]
            row_results = float(row_data.get("results") or 0)
            row_spend = float(row_data.get("spend") or 0)
            if row_results > 0:
                cost_val = row_spend / row_results

        costs.append(cost_val)
        budget_values.append(
            source_value(
                budget_matches,
                budget_by_id,
                stable_id,
                ("N/D", 0.0),
            ) if not ambiguous else ("N/D", 0.0)
        )

    result["cost_per_result"] = costs
    result["budget_display"] = [value[0] for value in budget_values]
    result["budget_total"] = [value[1] for value in budget_values]
    if {"spend", "impressions"}.issubset(result.columns):
        result["cpm"] = result["spend"].mul(1000).div(result["impressions"]).where(
            result["impressions"].gt(0), 0
        )
    if {"spend", "clicks"}.issubset(result.columns):
        result["cpc"] = result["spend"].div(result["clicks"]).where(
            result["clicks"].gt(0), 0
        )
    return result


def build_meta_campaign_total_row(frame, identity_labels=("Campaña",)):
    total_results = frame["results"].sum() if "results" in frame.columns else 0.0
    total_spend = frame["spend"].sum() if "spend" in frame.columns else 0.0
    total_impressions = frame["impressions"].sum() if "impressions" in frame.columns else 0.0
    total_clicks = frame["clicks"].sum() if "clicks" in frame.columns else 0.0
    cost_values = pd.to_numeric(frame["cost_per_result"], errors="coerce")
    cost_per_result = cost_values.mean()
    if pd.isna(cost_per_result) and total_results > 0:
        cost_per_result = total_spend / total_results
    budget_total = pd.to_numeric(
        frame.get("budget_total", pd.Series(dtype=float)), errors="coerce"
    ).fillna(0).sum()
    cost_display = f"${cost_per_result:,.2f}" if pd.notna(cost_per_result) else "N/D"
    cpm = total_spend * 1000 / total_impressions if total_impressions > 0 else 0
    cpc = total_spend / total_clicks if total_clicks > 0 else 0

    row = {label: "" for label in identity_labels}
    row[identity_labels[0]] = "TOTAL"
    row.update({
        "Tipo de resultado": "",
        "Resultados": f"{total_results:,.0f}",
        "Costo por resultado": cost_display,
        "Presupuesto": f"${budget_total:,.2f}",
        "CPM": f"${cpm:,.2f}",
        "Impresiones": f"{total_impressions:,.0f}",
        "Clics": f"{total_clicks:,.0f}",
        "CPC": f"${cpc:,.2f}",
        "Importe gastado": f"${total_spend:,.2f}",
    })
    return row


def dashboard_filter_options(df, column):
    if df.empty or column not in df.columns:
        return ["Todos"]
    values = df[column].dropna().astype(str).str.strip()
    return ["Todos"] + sorted(v for v in values.unique() if v)


def apply_dashboard_filters(df, campaign_filter, adset_filter, ad_filter):
    if campaign_filter and campaign_filter != "Todos" and "campaign_name" in df.columns:
        if isinstance(campaign_filter, list):
            campaign_names = {meta_base_campaign_name(value) for value in campaign_filter}
            df = df[df["campaign_name"].astype(str).apply(meta_base_campaign_name).isin(campaign_names)]
        else:
            df = df[df["campaign_name"].astype(str).apply(meta_base_campaign_name) == meta_base_campaign_name(campaign_filter)]
    for column, value in (("adset_name", adset_filter), ("ad_name", ad_filter)):
        if not value or value == "Todos" or column not in df.columns:
            continue
        if isinstance(value, (list, tuple, set)):
            df = df[df[column].astype(str).isin([str(item) for item in value])]
        else:
            df = df[df[column].astype(str) == value]
    return df


def campaign_title(selected_campaigns, fallback):
    names = list(dict.fromkeys(clean_campaign_name(meta_base_campaign_name(name)) for name in selected_campaigns if name))
    return " + ".join(names) if names else fallback


def get_current_month_range(ref_date):
    start = date(ref_date.year, ref_date.month, 1)
    return start, ref_date


# Get previous calendar month start and end dates
def get_prior_month_range(start_date):
    if start_date.month == 1:
        prev_month = 12
        prev_year = start_date.year - 1
    else:
        prev_month = start_date.month - 1
        prev_year = start_date.year

    prev_start = date(prev_year, prev_month, 1)
    last_day = calendar.monthrange(prev_year, prev_month)[1]
    prev_end = date(prev_year, prev_month, last_day)
    return prev_start, prev_end
