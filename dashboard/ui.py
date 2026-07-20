import streamlit as st
import altair as alt

def get_theme_colors():
    theme_mode = "Oscuro" if st.session_state.get("theme_switch", True) else "Claro"
    chart_bg = "#FFFFFF" if theme_mode == "Claro" else "#0A0D13"
    text_color = "#0F172A" if theme_mode == "Claro" else "#EAF0F7"
    grid_color = "rgba(15,23,42,0.10)" if theme_mode == "Claro" else "rgba(255,255,255,0.05)"
    title_color = "#0F172A" if theme_mode == "Claro" else "#EAF0F7"
    return chart_bg, text_color, grid_color, title_color


def theme_chart(chart):
    chart_bg, text_color, grid_color, _ = get_theme_colors()
    return chart.properties(background=chart_bg).configure_view(
        strokeOpacity=0,
        fill=chart_bg,
    ).configure_axis(
        gridColor=grid_color,
        labelColor=text_color,
        titleColor=text_color,
    ).configure_legend(
        labelColor=text_color,
        titleColor=text_color,
    )


def show_theme_table(df):
    st.markdown(df.to_html(index=False, classes="theme-table"), unsafe_allow_html=True)


def get_kpi_card_html(label, value_str, sub_str, curr_val, prev_val, lower_is_better=False):
    delta_html = ""
    if prev_val and prev_val > 0:
        pct_change = ((curr_val - prev_val) / prev_val) * 100
        is_good = pct_change < 0 if lower_is_better else pct_change > 0
        delta_class = "up" if is_good else "down"
        arrow = "&#9650;" if pct_change > 0 else "&#9660;"
        delta_html = f'<div class="delta {delta_class}">{arrow} {pct_change:+.1f}% vs. ant.</div>'
    else:
        delta_html = '<div class="delta up" style="background: rgba(255,255,255,0.06); color: #8A97A8;">N/D vs. ant.</div>'
    return f'<div class="kpi"><div><div class="lab">{label}</div><div class="val">{value_str}</div><div class="sub">{sub_str}</div></div>{delta_html}</div>'


def render_dashboard_empty_state(message):
    _, _, _, title_color = get_theme_colors()
    st.markdown(f"""
    <h1 style="margin-top: 10px; font-size: 2rem; line-height: 1.1; color: {title_color};">Selecciona una cuenta para empezar</h1>
    <p class="lede" style="margin-top: 15px;">{message}</p>
    """, unsafe_allow_html=True)
