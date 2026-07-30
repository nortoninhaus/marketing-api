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


def build_meta_campaign_total_row(frame, identity_labels=("Campaña",)):
    total_results = frame["results"].sum()
    total_spend = frame["spend"].sum()
    total_impressions = frame["impressions"].sum()
    total_clicks = frame["clicks"].sum()
    cost_per_result = frame["cost_per_result"].mean()
    cpm = total_spend * 1000 / total_impressions if total_impressions > 0 else 0
    cpc = total_spend / total_clicks if total_clicks > 0 else 0

    row = {label: "" for label in identity_labels}
    row[identity_labels[0]] = "TOTAL"
    row.update({
        "Tipo de resultado": "",
        "Resultados": f"{total_results:,.0f}",
        "Costo por resultado": f"${cost_per_result:,.2f}",
        "CPM": f"${cpm:,.2f}",
        "Impresiones": f"{total_impressions:,.0f}",
        "Clics": f"{total_clicks:,.0f}",
        "CPC": f"${cpc:,.2f}",
        "Inversión": f"${total_spend:,.2f}",
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
