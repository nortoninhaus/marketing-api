from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1].joinpath("dashboard.py").read_text()


def test_dashboard_has_light_dark_and_spanish_meta_labels():
    assert 'st.sidebar.toggle("☀️ / 🌙"' in SOURCE
    assert 'st.sidebar.radio("Tema", ["Claro", "Oscuro"]' not in SOURCE
    assert '"male": "Masculino"' in SOURCE
    assert '"female": "Femenino"' in SOURCE
    assert "Desempeño de campañas destacadas" in SOURCE
    assert "Ranking de hashtags (Instagram)" in SOURCE


def test_theme_change_does_not_refetch_official_meta_data():
    assert "dashboard_query_cache" in SOURCE
    assert "query_key" in SOURCE
    assert 'st.session_state["dashboard_query_cache"][query_key]' in SOURCE
    assert "meta_official_cache" in SOURCE
    assert "official_key" in SOURCE
    assert 'st.session_state["meta_official_cache"][official_key]' in SOURCE


def test_charts_and_header_follow_selected_theme():
    assert 'chart_bg = "#FFFFFF" if theme_mode == "Claro" else "#0A0D13"' in SOURCE
    assert 'text_color = "#0F172A" if theme_mode == "Claro" else "#EAF0F7"' in SOURCE
    assert ".agency img { filter:" in SOURCE


def test_dashboard_hashtag_ranking_uses_returned_post_text():
    assert "ad_hashtag_rows" in SOURCE
    assert "effective_object_story_id" in SOURCE
    assert '"post_message": post_text' in SOURCE
    assert 'preview.get("body", "")' in SOURCE
    assert 'preview.get("post_message", "")' in SOURCE
    assert 'text_col = "caption" if "caption" in df_curr.columns else "campaign_name"' in SOURCE
    assert 're.findall(r"#[\\wáéíóúÁÉÍÓÚñÑ]+", text)' in SOURCE
    assert "No se encontraron hashtags" in SOURCE


def test_regions_are_localized_and_charted():
    assert "clean_region_name" in SOURCE
    assert 're.sub(r"\\s+Province$"' in SOURCE
    assert 'st.markdown("#### Regiones principales")' in SOURCE
    assert "region_chart" in SOURCE


def test_campaign_names_are_cleaned_for_display():
    assert "clean_campaign_name" in SOURCE
    assert '"campaign_label": clean_campaign_name(campaign_name)' in SOURCE
    assert '"campaign_label": "Campaña"' in SOURCE


if __name__ == "__main__":
    test_dashboard_has_light_dark_and_spanish_meta_labels()
    test_theme_change_does_not_refetch_official_meta_data()
    test_charts_and_header_follow_selected_theme()
    test_dashboard_hashtag_ranking_uses_returned_post_text()
    test_regions_are_localized_and_charted()
    test_campaign_names_are_cleaned_for_display()
