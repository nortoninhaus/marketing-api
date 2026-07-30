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
