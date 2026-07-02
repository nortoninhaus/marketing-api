# ponytail: simple, dynamic marketing dashboard connecting to the API directly with period comparison and custom CSS styling
import streamlit as st
import pandas as pd
import requests
import json
import os
import textwrap
import calendar
import html
import altair as alt
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# Load env variables for local defaults
load_dotenv()
DEFAULT_API_KEY = os.getenv("API_KEY", "dev-key-change-me")
DEFAULT_API_URL = "https://inhaus-marketing-api-btdf7nijqa-uc.a.run.app"

# Determine sidebar collapse state dynamically to hide it automatically once query runs
initial_sidebar = "collapsed" if st.session_state.get("query_run", False) else "expanded"

# Page config to force wide layout
st.set_page_config(
    page_title="Inhaus Marketing API - Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state=initial_sidebar
)

# Custom premium styling helper supporting Light and Dark modes
def get_custom_css(theme_mode):
    if theme_mode == "light":
        return """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800&display=swap');
        
        div.stAppDeployButton {display: none !important;}
        footer {visibility: hidden !important;}
        [data-testid="stHeader"] {
            background-color: transparent !important;
            box-shadow: none !important;
        }
        #MainMenu {visibility: hidden !important;}
        
        .stApp {
            background-color: #F8F9FC !important;
            color: #1E293B !important;
            font-family: 'Manrope', sans-serif !important;
        }
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid rgba(0, 0, 0, 0.08) !important;
        }
        [data-testid="stSidebar"] h3 {
            color: #1E293B !important;
        }
        h1, h2, h3, h4, .sipy-word {
            font-family: 'Sora', sans-serif !important;
            font-weight: 800 !important;
            color: #0F172A !important;
        }
        .custom-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 0px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.08);
            margin-bottom: 30px;
        }
        .agency {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .agency img {
            height: 26px;
            width: auto;
            filter: invert(0.8) hue-rotate(180deg);
        }
        .agency .div-bar {
            width: 1px;
            height: 22px;
            background: rgba(0, 0, 0, 0.1);
        }
        .agency .who {
            font-size: 12px;
            color: #64748B;
            font-weight: 600;
            letter-spacing: .02em;
        }
        .stamp {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #64748B;
            font-weight: 600;
        }
        .stamp .live {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #059669;
            box-shadow: 0 0 0 0 rgba(5, 150, 105, 0.6);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(5, 150, 105, 0.5); }
            70% { box-shadow: 0 0 0 8px rgba(5, 150, 105, 0); }
            100% { box-shadow: 0 0 0 0 rgba(5, 150, 105, 0); }
        }
        
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: rgba(248, 249, 252, 0.95);
            z-index: 999999;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .loading-text {
            font-family: 'Sora', sans-serif;
            color: #059669;
            font-size: 24px;
            margin-top: 20px;
            font-weight: 800;
        }
        .spinner {
            border: 6px solid rgba(0, 0, 0, 0.05);
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border-left-color: #059669;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .eyebrow {
            font-size: 11px;
            font-weight: 800;
            letter-spacing: .2em;
            text-transform: uppercase;
            color: #059669;
        }
        .lede {
            color: #475569;
            font-size: 15px;
            max-width: 800px;
            font-weight: 500;
            line-height: 1.5;
            margin-bottom: 20px;
        }
        
        .hero-card {
            background: linear-gradient(165deg, #FFFFFF, #F1F5F9);
            border: 1px solid rgba(0,0,0,0.08);
            border-radius: 24px;
            padding: 30px;
            position: relative;
            overflow: hidden;
            margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.04);
            color: #1E293B;
        }
        .hero-card .lab {
            font-size: 12px;
            color: #64748B;
            font-weight: 700;
            letter-spacing: .02em;
        }
        .hero-card .big {
            font-family: 'Sora', sans-serif;
            font-weight: 800;
            font-size: 60px;
            line-height: .9;
            letter-spacing: -.04em;
            margin-top: 6px;
            color: #059669;
        }
        
        .kpis {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
            margin-top: 10px;
            margin-bottom: 25px;
        }
        .kpi {
            background: #FFFFFF;
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 18px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 140px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.02);
            color: #1E293B;
        }
        .kpi .lab {
            font-size: 12px;
            color: #64748B;
            font-weight: 700;
        }
        .kpi .val {
            font-family: 'Sora', sans-serif;
            font-weight: 800;
            font-size: 28px;
            letter-spacing: -.03em;
            margin-top: 10px;
            color: #0F172A;
        }
        .kpi .sub {
            font-size: 12px;
            color: #94A3B8;
            font-weight: 600;
            margin-top: 7px;
        }
        
        .stTable {
            background-color: #FFFFFF !important;
            border: 1px solid rgba(0, 0, 0, 0.08) !important;
            border-radius: 18px !important;
        }
        
        .delta {
            display: inline-flex;
            align-items: center;
            gap: 3px;
            font-size: 11px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 6px;
            margin-top: 9px;
            width: fit-content;
        }
        .delta.up {
            background: rgba(5, 150, 105, 0.1);
            color: #059669;
        }
        .delta.down {
            background: rgba(220, 38, 38, 0.1);
            color: #DC2626;
        }
        
        /* Post Card Styling (Light) */
        .post-card {
            background: #FFFFFF;
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 16px;
            display: flex;
            flex-direction: column;
            height: 100%;
            box-shadow: 0 4px 12px rgba(0,0,0,0.04);
            position: relative;
        }
        .post-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }
        .post-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: #059669;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 14px;
            color: #FFFFFF;
        }
        .post-author {
            font-size: 14px;
            font-weight: 700;
            color: #0F172A;
        }
        .post-time {
            font-size: 11px;
            color: #64748B;
        }
        .post-body {
            font-size: 13px;
            color: #334155;
            margin-bottom: 12px;
            line-height: 1.4;
            min-height: 54px;
        }
        .post-image {
            width: 100%;
            height: 180px;
            object-fit: cover;
            border-radius: 10px;
            background-color: #F1F5F9;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748B;
            font-size: 12px;
            border: 1px solid rgba(0,0,0,0.05);
        }
        .post-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(0, 0, 0, 0.08);
            padding-top: 10px;
            margin-top: auto;
        }
        .post-metric-label {
            font-size: 11px;
            color: #64748B;
            font-weight: 600;
        }
        .post-metric-value {
            font-size: 13px;
            font-weight: 800;
            color: #0F172A;
        }
        .post-badge {
            position: absolute;
            top: -10px;
            right: -10px;
            background: #FF8F1F;
            color: #FFFFFF;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 13px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            z-index: 10;
        }
        .reel-image {
            width: 100%;
            height: 240px;
            object-fit: cover;
            border-radius: 12px;
            background-color: #F1F5F9;
            margin-bottom: 12px;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(0,0,0,0.05);
        }
        .play-btn {
            width: 50px;
            height: 50px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #0F172A;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        }
        </style>
        """
    else:
        return """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800&display=swap');
        
        div.stAppDeployButton {display: none !important;}
        footer {visibility: hidden !important;}
        [data-testid="stHeader"] {
            background-color: transparent !important;
            box-shadow: none !important;
        }
        #MainMenu {visibility: hidden !important;}
        
        .stApp {
            background-color: #0A0D13 !important;
            color: #EAF0F7 !important;
            font-family: 'Manrope', sans-serif !important;
        }
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
        }
        [data-testid="stSidebar"] {
            background-color: #121823 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        }
        h1, h2, h3, h4, .sipy-word {
            font-family: 'Sora', sans-serif !important;
            font-weight: 800 !important;
            color: #EAF0F7 !important;
        }
        .custom-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 0px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            margin-bottom: 30px;
        }
        .agency {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .agency img {
            height: 26px;
            width: auto;
        }
        .agency .div-bar {
            width: 1px;
            height: 22px;
            background: rgba(255,255,255,0.14);
        }
        .agency .who {
            font-size: 12px;
            color: #8A97A8;
            font-weight: 600;
            letter-spacing: .02em;
        }
        .stamp {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #8A97A8;
            font-weight: 600;
        }
        .stamp .live {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #1AE08C;
            box-shadow: 0 0 0 0 rgba(26,224,140,0.6);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(26,224,140,0.5); }
            70% { box-shadow: 0 0 0 8px rgba(26,224,140,0); }
            100% { box-shadow: 0 0 0 0 rgba(26,224,140,0); }
        }
        
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: rgba(10, 13, 19, 0.95);
            z-index: 999999;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .loading-text {
            font-family: 'Sora', sans-serif;
            color: #1AE08C;
            font-size: 24px;
            margin-top: 20px;
            font-weight: 800;
        }
        .spinner {
            border: 6px solid rgba(255, 255, 255, 0.1);
            width: 70px;
            height: 70px;
            border-radius: 50%;
            border-left-color: #1AE08C;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .eyebrow {
            font-size: 11px;
            font-weight: 800;
            letter-spacing: .2em;
            text-transform: uppercase;
            color: #1AE08C;
        }
        .lede {
            color: #8A97A8;
            font-size: 15px;
            max-width: 800px;
            font-weight: 500;
            line-height: 1.5;
            margin-bottom: 20px;
        }
        
        .hero-card {
            background: linear-gradient(165deg, #161E2B, #0F1620);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 24px;
            padding: 30px;
            position: relative;
            overflow: hidden;
            margin-bottom: 25px;
            color: #EAF0F7;
        }
        .hero-card .lab {
            font-size: 12px;
            color: #8A97A8;
            font-weight: 700;
            letter-spacing: .02em;
        }
        .hero-card .big {
            font-family: 'Sora', sans-serif;
            font-weight: 800;
            font-size: 60px;
            line-height: .9;
            letter-spacing: -.04em;
            margin-top: 6px;
            color: #1AE08C;
        }
        
        .kpis {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
            margin-top: 10px;
            margin-bottom: 25px;
        }
        .kpi {
            background: #121823;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 140px;
            color: #EAF0F7;
        }
        .kpi .lab {
            font-size: 12px;
            color: #8A97A8;
            font-weight: 700;
        }
        .kpi .val {
            font-family: 'Sora', sans-serif;
            font-weight: 800;
            font-size: 28px;
            letter-spacing: -.03em;
            margin-top: 10px;
            color: #EAF0F7;
        }
        .kpi .sub {
            font-size: 12px;
            color: #5E6A7A;
            font-weight: 600;
            margin-top: 7px;
        }
        
        .stTable {
            background-color: #121823 !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 18px !important;
        }
        
        .delta {
            display: inline-flex;
            align-items: center;
            gap: 3px;
            font-size: 11px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 6px;
            margin-top: 9px;
            width: fit-content;
        }
        .delta.up {
            background: rgba(26,224,140,0.14);
            color: #1AE08C;
        }
        .delta.down {
            background: rgba(255,107,107,0.14);
            color: #FF6B6B;
        }
        
        /* Post Card Styling (Dark) */
        .post-card {
            background: #121823;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 16px;
            display: flex;
            flex-direction: column;
            height: 100%;
            position: relative;
        }
        .post-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }
        .post-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: #1AE08C;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 14px;
            color: #0A0D13;
        }
        .post-author {
            font-size: 14px;
            font-weight: 700;
            color: #EAF0F7;
        }
        .post-time {
            font-size: 11px;
            color: #8A97A8;
        }
        .post-body {
            font-size: 13px;
            color: #EAF0F7;
            margin-bottom: 12px;
            line-height: 1.4;
            min-height: 54px;
        }
        .post-image {
            width: 100%;
            height: 180px;
            object-fit: cover;
            border-radius: 10px;
            background-color: #1A2333;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #5E6A7A;
            font-size: 12px;
        }
        .post-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 10px;
            margin-top: auto;
        }
        .post-metric-label {
            font-size: 11px;
            color: #8A97A8;
            font-weight: 600;
        }
        .post-metric-value {
            font-size: 13px;
            font-weight: 800;
            color: #EAF0F7;
        }
        .post-badge {
            position: absolute;
            top: -10px;
            right: -10px;
            background: #FF8F1F;
            color: #FFFFFF;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 13px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            z-index: 10;
        }
        .reel-image {
            width: 100%;
            height: 240px;
            object-fit: cover;
            border-radius: 12px;
            background-color: #1A2333;
            margin-bottom: 12px;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .play-btn {
            width: 50px;
            height: 50px;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #0A0D13;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }
        </style>
        """

# Featured campaigns table builder matching Image 1
def get_featured_campaigns_table_html(theme_mode):
    campaigns = [
        {"name": "Nutri / Interacción / FB-IG", "impressions": "893,691", "result_val": "63,106", "result_type": "Int"},
        {"name": "Nutri / Alcance / FB-IG", "impressions": "501,140", "result_val": "878", "result_type": "Clics"},
        {"name": "Nutri / Parrilla / Alcance", "impressions": "727,139", "result_val": "210", "result_type": "Clics"},
    ]
    border_color = "rgba(255,255,255,0.08)" if theme_mode == "dark" else "rgba(0,0,0,0.08)"
    bg_header = "#121823" if theme_mode == "dark" else "#F1F5F9"
    text_header = "#8A97A8" if theme_mode == "dark" else "#475569"
    text_color = "#EAF0F7" if theme_mode == "dark" else "#0F172A"
    
    html = f"""
    <table style="width:100%; border-collapse: collapse; border: 1px solid {border_color}; border-radius: 12px; overflow: hidden; font-family: 'Manrope', sans-serif;">
        <thead>
            <tr style="background: {bg_header}; border-bottom: 1px solid {border_color}; text-align: left; font-size: 12px; font-weight: 800; color: {text_header}; text-transform: uppercase;">
                <th style="padding: 12px 16px;">Nombre de Campaña</th>
                <th style="padding: 12px 16px; text-align: center;">Impresiones</th>
                <th style="padding: 12px 16px; text-align: center;">Resultados</th>
            </tr>
        </thead>
        <tbody style="font-size: 13px; font-weight: 600; color: {text_color};">
    """
    for item in campaigns:
        res_color = "#1AE08C" if theme_mode == "dark" else "#059669"
        html += f"""
            <tr style="border-bottom: 1px solid {border_color};">
                <td style="padding: 12px 16px; font-weight: 700;">{item['name']}</td>
                <td style="padding: 12px 16px; text-align: center;">{item['impressions']}</td>
                <td style="padding: 12px 16px; text-align: center; color: {res_color}; font-weight: 700;">{item['result_val']} ({item['result_type']})</td>
            </tr>
        """
    html += """
        </tbody>
    </table>
    """
    return html

# Hashtags table builder matching Image 3 (highlighting #humornutri in pink)
def get_hashtags_table_html(theme_mode):
    hashtags = [
        {"tag": "#loncheranutri", "posts": 1, "views": "59.72k", "likes": 7, "comments": 0, "highlight": False},
        {"tag": "#nutrientudía", "posts": 1, "views": "59.72k", "likes": 7, "comments": 0, "highlight": False},
        {"tag": "#hechoconnutri", "posts": 1, "views": "59.72k", "likes": 7, "comments": 0, "highlight": False},
        {"tag": "#humornutri", "posts": 2, "views": "31.48k", "likes": 31, "comments": 18, "highlight": True},
        {"tag": "#momentosnutri", "posts": 7, "views": "27.12k", "likes": 23, "comments": 6, "highlight": False},
        {"tag": "#nutrientumesa", "posts": 3, "views": "20.99k", "likes": 21, "comments": 1, "highlight": False},
        {"tag": "#nutri", "posts": 9, "views": "17.09k", "likes": 21, "comments": 5, "highlight": False},
        {"tag": "#trayectorianutri", "posts": 1, "views": "14.71k", "likes": 17, "comments": 1, "highlight": False},
        {"tag": "#familiasecuatorianas", "posts": 1, "views": "14.71k", "likes": 17, "comments": 1, "highlight": False},
        {"tag": "#nutri50años", "posts": 2, "views": "11.21k", "likes": 17, "comments": 0, "highlight": False},
    ]
    
    border_color = "rgba(255,255,255,0.08)" if theme_mode == "dark" else "rgba(0,0,0,0.08)"
    bg_header = "#121823" if theme_mode == "dark" else "#F1F5F9"
    text_header = "#8A97A8" if theme_mode == "dark" else "#475569"
    text_color = "#EAF0F7" if theme_mode == "dark" else "#0F172A"
    
    html = f"""
    <table style="width:100%; border-collapse: collapse; border: 1px solid {border_color}; border-radius: 12px; overflow: hidden; font-family: 'Manrope', sans-serif;">
        <thead>
            <tr style="background: {bg_header}; border-bottom: 1px solid {border_color}; text-align: left; font-size: 12px; font-weight: 800; color: {text_header}; text-transform: uppercase;">
                <th style="padding: 12px 16px;">Hashtag</th>
                <th style="padding: 12px 16px; text-align: center;">Posts</th>
                <th style="padding: 12px 16px; text-align: center;">Visualizaciones</th>
                <th style="padding: 12px 16px; text-align: center;">Me Gusta</th>
                <th style="padding: 12px 16px; text-align: center;">Comentarios</th>
            </tr>
        </thead>
        <tbody style="font-size: 13px; font-weight: 600; color: {text_color};">
    """
    for item in hashtags:
        row_style = ""
        tag_color = "#D61F69" if item["highlight"] else ("#1AE08C" if theme_mode == "dark" else "#059669")
        if item["highlight"]:
            row_bg = "rgba(244,63,94,0.08)" if theme_mode == "dark" else "rgba(244,63,94,0.05)"
            row_style = f"background: {row_bg}; color: #F43F5E;"
        
        html += f"""
            <tr style="border-bottom: 1px solid {border_color}; {row_style}">
                <td style="padding: 12px 16px; color: {tag_color if item['highlight'] else text_color}; font-weight: 700;">{item['tag']}</td>
                <td style="padding: 12px 16px; text-align: center;">{item['posts']}</td>
                <td style="padding: 12px 16px; text-align: center;">{item['views']}</td>
                <td style="padding: 12px 16px; text-align: center;">{item['likes']}</td>
                <td style="padding: 12px 16px; text-align: center;">{item['comments']}</td>
            </tr>
        """
    html += """
        </tbody>
    </table>
    """
    return html

# Helper function to extract metrics robustly
def extract_metric(metrics, keys):
    for key in keys:
        if key in metrics and metrics[key] is not None:
            try:
                return float(metrics[key])
            except ValueError:
                pass
    return 0.0

# Fetch connected accounts
@st.cache_data(ttl=300, show_spinner=False)
def fetch_connections_from_api(platform_key, client_id, api_key):
    url = f"{DEFAULT_API_URL}/api/v1/oauth/connections"
    headers = {
        "accept": "*/*",
        "x-api-key": api_key,
        "origin": "https://inhaus-marketing-api.web.app",
        "referer": "https://inhaus-marketing-api.web.app/"
    }
    params = {"platform": platform_key, "client_id": client_id}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        if res.status_code == 200:
            return res.json().get("data", [])
        return []
    except Exception:
        return []

# Fetch fields schema
@st.cache_data(ttl=600, show_spinner=False)
def fetch_schema_from_api(platform_key, api_key):
    url = f"{DEFAULT_API_URL}/api/v1/schema"
    headers = {
        "accept": "*/*",
        "x-api-key": api_key,
        "origin": "https://inhaus-marketing-api.web.app",
        "referer": "https://inhaus-marketing-api.web.app/"
    }
    params = {"platform": platform_key}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        if res.status_code == 200:
            return res.json().get("data", {"metrics": [], "dimensions": []})
        return {"metrics": [], "dimensions": []}
    except Exception:
        return {"metrics": [], "dimensions": []}

# Fetch campaign data from API proxy
@st.cache_data(ttl=120, show_spinner=False)
def fetch_campaign_data_from_api(platform_key, client_id, user_id, account_id, start_date, end_date, metrics, dimensions, opt_filters, write_to_bq, api_key, show_errors=True, timeout=45):
    url = f"{DEFAULT_API_URL}/api/v1/campaign-data"
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "x-api-key": api_key,
        "origin": "https://inhaus-marketing-api.web.app",
        "referer": "https://inhaus-marketing-api.web.app/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    }
    payload = {
        "platform": platform_key,
        "client_id": client_id,
        "user_id": user_id,
        "account_id": account_id,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "metrics": metrics
    }
    if dimensions:
        payload["dimensions"] = dimensions
    if write_to_bq:
        payload["write_to_bq"] = True
        
    payload.update(opt_filters)
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if res.status_code == 200:
            return res.json().get("data", [])
        else:
            if show_errors:
                st.error(f"Error de API ({res.status_code}): {res.text}")
            return []
    except Exception as e:
        if show_errors:
            st.error(f"Error de conexión con la API: {e}")
        return []

# Fetch Meta previews
@st.cache_data(ttl=300, show_spinner=False)
def fetch_meta_campaign_previews(client_id, account_id, campaign_names, api_key):
    campaign_names = tuple(name for name in campaign_names if name and name != "N/A")
    if not campaign_names:
        return [], None

    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "x-api-key": api_key,
        "origin": "https://inhaus-marketing-api.web.app",
        "referer": "https://inhaus-marketing-api.web.app/",
    }
    url = f"{DEFAULT_API_URL}/api/v1/meta-proxy"
    account_edge = account_id if str(account_id).startswith("act_") else f"act_{account_id}"

    def meta_get(path, params, timeout=30):
        return requests.post(url, headers=headers, json={
            "client_id": client_id,
            "account_id": account_id,
            "path": path,
            "method": "GET",
            "params": params,
        }, timeout=timeout)

    try:
        ads_res = meta_get(f"{account_edge}/ads", {
            "fields": "id,name,campaign{id,name}",
            "limit": 200,
        })
        if ads_res.status_code != 200:
            return [], f"No se pudieron cargar anuncios Meta ({ads_res.status_code})."

        wanted = set(campaign_names)
        ads_by_campaign = {}
        for ad in ads_res.json().get("data", []):
            campaign_name = (ad.get("campaign") or {}).get("name")
            if campaign_name in wanted and campaign_name not in ads_by_campaign:
                ads_by_campaign[campaign_name] = ad

        previews = []
        for campaign_name in campaign_names:
            ad = ads_by_campaign.get(campaign_name)
            if not ad:
                continue
            preview_res = meta_get(f"{ad['id']}/previews", {"ad_format": "DESKTOP_FEED_STANDARD"}, timeout=20)
            if preview_res.status_code != 200:
                continue
            body = (preview_res.json().get("data") or [{}])[0].get("body")
            if body:
                previews.append({
                    "campaign_name": campaign_name,
                    "ad_name": ad.get("name") or "",
                    "body": body,
                })

        return previews, None if previews else "No se encontraron previews para las campañas del resultado."
    except Exception as e:
        return [], f"Error cargando previews Meta: {e}"

# Process results
def process_api_response(api_data, platform_key, client_id, user_id):
    flat_rows = []
    for item in api_data:
        metrics = item.get("metrics", {})
        dimensions = item.get("dimensions", {})
        
        row = {}
        row["campaign_name"] = dimensions.get("campaign_name") or dimensions.get("ad_name") or dimensions.get("post_id") or "N/A"
        row["platform"] = platform_key
        
        dt_val = dimensions.get("date") or dimensions.get("timestamp")
        if dt_val:
            try:
                row["date"] = pd.to_datetime(dt_val)
            except Exception:
                row["date"] = pd.to_datetime(date.today())
        else:
            row["date"] = pd.to_datetime(date.today())
            
        for dim, val in dimensions.items():
            if dim not in ["campaign_name", "ad_name", "post_id", "date", "timestamp"]:
                # Translate demographic values to Spanish immediately
                if dim == "gender":
                    val_str = str(val).lower()
                    if val_str in ["male", "masculino"]:
                        val = "Masculino"
                    elif val_str in ["female", "femenino"]:
                        val = "Femenino"
                    else:
                        val = "Desconocido"
                row[dim] = val
                
        row["spend"] = extract_metric(metrics, ["spend", "spend_amount", "cost", "amount_spent"])
        row["impressions"] = extract_metric(metrics, ["impressions", "impression_count", "views"])
        row["clicks"] = extract_metric(metrics, ["clicks", "click_count", "link_clicks"])
        row["conversions"] = extract_metric(metrics, ["conversions", "conversion_count", "purchases", "leads", "actions"])
        row["reach"] = extract_metric(metrics, ["reach", "reach_count", "unique_impressions"])
        row["engagement"] = extract_metric(metrics, ["engagement", "engagements", "engagement_count", "interactions"])
        row["followers"] = extract_metric(metrics, ["followers", "follower_count", "new_followers"])
        row["sessions"] = extract_metric(metrics, ["sessions", "session_count"])
        row["users"] = extract_metric(metrics, ["users", "active_users", "visitor_count"])
        row["pageviews"] = extract_metric(metrics, ["pageviews", "screen_views", "views"])
        row["bounce_rate"] = extract_metric(metrics, ["bounce_rate", "bounce"])
        row["downloads"] = extract_metric(metrics, ["downloads", "installs", "app_units"])
        row["ratings"] = extract_metric(metrics, ["ratings", "rating_score", "average_rating"])
        
        flat_rows.append(row)
        
    if not flat_rows:
        return pd.DataFrame(columns=[
            "campaign_name", "platform", "date", "spend", "impressions", "clicks", 
            "conversions", "reach", "engagement", "followers", "sessions", "users", "pageviews", "bounce_rate", "downloads", "ratings"
        ])
    return pd.DataFrame(flat_rows)

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

# Platform Types
PLATFORM_TYPES = {
    "meta_ads": "ads",
    "google_ads": "ads",
    "tiktok_ads": "ads",
    "linkedin_ads": "ads",
    "apple_ads": "ads",
    "x_ads": "ads",
    "spotify_ads": "ads",
    "pinterest_ads": "ads",
    "meta_organic": "organic",
    "tiktok_organic": "organic",
    "linkedin_organic": "organic",
    "x_organic": "organic",
    "youtube": "organic",
    "threads": "organic",
    "pinterest_organic": "organic",
    "ga4": "analytics",
    "shopify": "analytics",
    "ghl": "analytics",
    "google_play": "app_store",
    "apple_app_store": "app_store",
}

# SIDEBAR FILTERS
st.sidebar.image("https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg", width=120)

# Theme Selector
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"
theme = st.sidebar.selectbox("Tema Visual", ["Oscuro (Dark)", "Claro (Light)"], index=0 if st.session_state.theme_mode == "dark" else 1)
theme_mode = "dark" if "Oscuro" in theme else "light"
st.session_state.theme_mode = theme_mode

# Inject dynamic CSS based on theme mode
st.markdown(get_custom_css(theme_mode), unsafe_allow_html=True)

st.sidebar.markdown("### Configuración de Consulta")

api_key = st.sidebar.text_input("X-API-Key", value=DEFAULT_API_KEY, type="password")
client_id = st.sidebar.text_input("Client ID", value="client_1")
user_id = st.sidebar.text_input("User ID", value="user_1")

platform_labels = {
    "meta_ads": "Meta Ads (Facebook/IG)",
    "google_ads": "Google Ads",
    "tiktok_ads": "TikTok Ads",
    "linkedin_ads": "LinkedIn Ads",
    "apple_ads": "Apple Search Ads",
    "x_ads": "X Ads",
    "spotify_ads": "Spotify Ads",
    "pinterest_ads": "Pinterest Ads",
    "meta_organic": "Meta Organic",
    "tiktok_organic": "TikTok Organic",
    "linkedin_organic": "LinkedIn Organic",
    "x_organic": "X Organic",
    "youtube": "YouTube Analytics",
    "threads": "Threads Organic",
    "pinterest_organic": "Pinterest Organic",
    "ga4": "Google Analytics 4",
    "shopify": "Shopify Analytics",
    "ghl": "GoHighLevel CRM",
    "google_play": "Google Play Console",
    "apple_app_store": "Apple App Store",
}

platform_key = st.sidebar.selectbox(
    "Plataforma", 
    options=list(platform_labels.keys()), 
    format_func=lambda x: platform_labels[x]
)

platform_type = PLATFORM_TYPES.get(platform_key, "ads")
selected_platform_label = platform_labels[platform_key]

# Fetch connected accounts
connections = fetch_connections_from_api(platform_key, client_id, api_key)
account_options = {}
if connections:
    for conn in connections:
        account_options[conn["account_id"]] = f"{conn['account_name']} ({conn['account_id']})"

if account_options:
    account_id = st.sidebar.selectbox(
        "Cuenta Conectada", 
        options=list(account_options.keys()),
        format_func=lambda x: account_options[x]
    )
else:
    account_id = st.sidebar.text_input("Account ID (Ingresa manualmente)", value="act_1")

# Fetch fields schema
schema = fetch_schema_from_api(platform_key, api_key)
metrics_list = schema.get("metrics") or []
dimensions_list = schema.get("dimensions") or []

# Default metrics selection
default_selected_metrics = []
if platform_type == "ads":
    default_selected_metrics = ["spend", "impressions", "clicks", "conversions", "reach"]
elif platform_type == "analytics":
    default_selected_metrics = ["sessions", "users", "pageviews"]
elif platform_type == "app_store":
    default_selected_metrics = ["downloads", "ratings"]
else:
    default_selected_metrics = ["impressions", "engagement", "followers"]

default_selected_metrics = [m for m in default_selected_metrics if m in [x["name"] for x in metrics_list]]

selected_metrics = st.sidebar.multiselect(
    "Métricas",
    options=[x["name"] for x in metrics_list],
    default=default_selected_metrics if default_selected_metrics else None,
    format_func=lambda x: next((item.get("display_name", x) for item in metrics_list if item.get("name") == x), x)
)

default_selected_dims = ["campaign_name", "date"] if "campaign_name" in [x["name"] for x in dimensions_list] else []
selected_dimensions = st.sidebar.multiselect(
    "Dimensiones Adicionales",
    options=[x["name"] for x in dimensions_list if x["name"] != "date"],
    default=[d for d in default_selected_dims if d != "date"],
    format_func=lambda x: next((item.get("display_name", x) for item in dimensions_list if item.get("name") == x), x)
)

# Force 'date' dimension
if "date" not in selected_dimensions and "date" in [x["name"] for x in dimensions_list]:
    selected_dimensions.append("date")

# Platform specific optional payload configurations
opt_filters = {}
st.sidebar.markdown("### Filtros Contextuales")

if platform_key == "meta_ads":
    action_report = st.sidebar.selectbox("Tipo de Conversión", ["Default", "Purchase", "Lead", "Add to Cart"], index=0)
    if action_report != "Default":
        opt_filters["action_report_time"] = action_report.lower().replace(" ", "_")
        
    attribution_window = st.sidebar.selectbox("Ventana de Atribución", ["Default", "1d_click", "7d_click", "1d_view"], index=0)
    if attribution_window != "Default":
        opt_filters["attribution_window"] = attribution_window

elif platform_key == "google_ads":
    conversion_category = st.sidebar.text_input("Categoría de Conversión (Opcional)", value="")
    if conversion_category:
        opt_filters["conversion_category"] = conversion_category

elif platform_key == "ga4":
    custom_events = st.sidebar.text_input("Eventos Personalizados (separados por coma)", value="")
    if custom_events:
        opt_filters["custom_events"] = [e.strip() for e in custom_events.split(",")]

write_to_bq = st.sidebar.checkbox("Respaldar consulta en BigQuery (Historial)", value=False)

# Date Picker
today = date.today()
default_start = today - timedelta(days=30)
date_range = st.sidebar.date_input("Rango de Fechas a Consultar", [default_start, today])

st.sidebar.markdown("---")
execute_query = st.sidebar.button("🚀 Consultar API de Producción", use_container_width=True)

# MAIN DISPLAY
# Header
st.markdown(f"""
<div class="custom-header">
    <div class="agency">
        <img src="https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg" alt="Inhaus">
        <span class="div-bar"></span>
        <span class="who">Dashboard de Pauta &middot; Conexión de API</span>
    </div>
    <span class="stamp"><span class="live"></span> API Directa</span>
</div>
""", unsafe_allow_html=True)

if execute_query:
    st.session_state.query_run = True
    st.rerun()

if not st.session_state.get("query_run", False):
    st.info("Configura tus parámetros de consulta en el menú hamburguesa lateral izquierdo y presiona el botón 'Consultar API de Producción' para cargar la visualización en pantalla completa.")
else:
    # Render the fullscreen loading overlay
    loading_placeholder = st.empty()
    loading_placeholder.markdown("""
        <div class="loading-overlay">
        <div class="spinner"></div>
        <div class="loading-text">1/3: Conectando con la API de Inhaus y solicitando periodo actual...</div>
        </div>
        """, unsafe_allow_html=True)

    # Resolve dates
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range[0], date_range[1]
    else:
        start_date, end_date = default_start, today
        
    prev_start_date, prev_end_date = get_prior_month_range(start_date)
    
    # Ensure standard KPI metrics are requested in payload even if unchecked
    request_metrics = list(selected_metrics)
    if platform_type == "ads":
        for m in ["impressions", "clicks", "spend", "conversions", "reach"]:
            if m not in request_metrics and m in [x["name"] for x in metrics_list]:
                request_metrics.append(m)
    elif platform_type == "analytics":
        for m in ["sessions", "users", "pageviews", "bounce_rate"]:
            if m not in request_metrics and m in [x["name"] for x in metrics_list]:
                request_metrics.append(m)
    elif platform_type == "app_store":
        for m in ["downloads", "ratings"]:
            if m not in request_metrics and m in [x["name"] for x in metrics_list]:
                request_metrics.append(m)
    else:
        for m in ["impressions", "engagement", "followers", "reach"]:
            if m not in request_metrics and m in [x["name"] for x in metrics_list]:
                request_metrics.append(m)
                
    curr_data = fetch_campaign_data_from_api(
        platform_key, client_id, user_id, account_id, 
        start_date, end_date, request_metrics, selected_dimensions, 
        opt_filters, write_to_bq, api_key
    )
    
    loading_placeholder.markdown("""
        <div class="loading-overlay">
            <div class="spinner"></div>
            <div class="loading-text">2/3: Procesando periodo actual y solicitando comparativa del mes anterior...</div>
        </div>
    """, unsafe_allow_html=True)
    
    prev_data = fetch_campaign_data_from_api(
        platform_key, client_id, user_id, account_id, 
        prev_start_date, prev_end_date, request_metrics, selected_dimensions, 
        opt_filters, False, api_key
    )
    
    loading_placeholder.markdown("""
        <div class="loading-overlay">
            <div class="spinner"></div>
            <div class="loading-text">3/3: Calculando métricas y estructurando tendencias PoP...</div>
        </div>
    """, unsafe_allow_html=True)
    
    loading_placeholder.empty()
    
    # Inject JavaScript to collapse sidebar
    import streamlit.components.v1 as components
    components.html("""
        <script>
        (function() {
            const parentDoc = window.parent.document;
            const collapseSidebar = () => {
                const collapseBtn = parentDoc.querySelector(
                    '[data-testid="stSidebarCollapseButton"], button[aria-label="Close sidebar"], button[title="Close sidebar"]'
                );
                if (collapseBtn) collapseBtn.click();
            };
            collapseSidebar();
            setTimeout(collapseSidebar, 200);
            setTimeout(collapseSidebar, 500);
        })();
        </script>
    """, height=0, width=0)
    
    if not curr_data:
        st.error("No se recibió información de la API para el periodo actual. Verifica las credenciales, plataforma o ID de cuenta en el menú lateral.")
    else:
        df_curr = process_api_response(curr_data, platform_key, client_id, user_id)
        df_prev = process_api_response(prev_data, platform_key, client_id, user_id) if prev_data else pd.DataFrame()
        
        # Resolve account label
        account_disp = account_id
        if connections:
            matched_name = [c["account_name"] for c in connections if c["account_id"] == account_id]
            if matched_name:
                account_disp = f"{matched_name[0]} ({account_id})"
                
        title_color = "#0F172A" if theme_mode == "light" else "#EAF0F7"
        st.markdown(f"""
        <h1 style="margin-top: 10px; font-size: 2.8rem; line-height: 1.1; color: {title_color}; font-weight: 800;">{selected_platform_label} &middot; {account_disp}</h1>
        <p class="lede" style="margin-top: 15px;">
            Resultados del <b>{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}</b>.<br/>
            Comparado contra mes anterior completo: <b>{prev_start_date.strftime('%d/%m/%Y')} al {prev_end_date.strftime('%d/%m/%Y')}</b>.
        </p>
        """, unsafe_allow_html=True)

        is_meta = platform_key in ["meta_ads", "meta_organic"]
        if is_meta:
            tab_general, tab_featured, tab_content = st.tabs([
                "📊 Dashboard General", 
                "⚡ Desempeño de Campañas", 
                "📱 Contenido Orgánico & Hashtags"
            ])
        else:
            tab_general = st.container()

        with tab_general:
            # Primary KPI calculations
            if platform_type == "ads":
                curr_primary = df_curr["conversions"].sum()
                prev_primary = df_prev["conversions"].sum() if not df_prev.empty else 0
                primary_label = "Conversiones Totales"
            elif platform_type == "analytics":
                curr_primary = df_curr["sessions"].sum()
                prev_primary = df_prev["sessions"].sum() if not df_prev.empty else 0
                primary_label = "Sesiones Totales"
            elif platform_type == "app_store":
                curr_primary = df_curr["downloads"].sum()
                prev_primary = df_prev["downloads"].sum() if not df_prev.empty else 0
                primary_label = "Descargas Totales"
            else:
                curr_primary = df_curr["engagement"].sum()
                prev_primary = df_prev["engagement"].sum() if not df_prev.empty else 0
                primary_label = "Engagement Total"
                
            st.markdown(f"""
            <div class="hero-card">
                <div class="lab">{primary_label}</div>
                <div class="big">{curr_primary:,}</div>
            </div>
            """, unsafe_allow_html=True)
            
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

            st.markdown("### Métricas Clave (KPIs) con Comparación")
            
            if platform_type == "ads":
                total_spend_curr = df_curr["spend"].sum()
                total_impressions_curr = df_curr["impressions"].sum()
                total_clicks_curr = df_curr["clicks"].sum()
                total_conversions_curr = df_curr["conversions"].sum()
                
                avg_ctr_curr = total_clicks_curr / total_impressions_curr if total_impressions_curr > 0 else 0.0
                avg_cpc_curr = total_spend_curr / total_clicks_curr if total_clicks_curr > 0 else 0.0
                cpa_curr = total_spend_curr / total_conversions_curr if total_conversions_curr > 0 else 0.0

                total_spend_prev = df_prev["spend"].sum() if not df_prev.empty else 0.0
                total_impressions_prev = df_prev["impressions"].sum() if not df_prev.empty else 0.0
                total_clicks_prev = df_prev["clicks"].sum() if not df_prev.empty else 0.0
                total_conversions_prev = df_prev["conversions"].sum() if not df_prev.empty else 0.0
                
                avg_ctr_prev = total_clicks_prev / total_impressions_prev if total_impressions_prev > 0 else 0.0
                avg_cpc_prev = total_spend_prev / total_clicks_prev if total_clicks_prev > 0 else 0.0
                cpa_prev = total_spend_prev / total_conversions_prev if total_conversions_prev > 0 else 0.0

                kpis_layout = '<div class="kpis">\n'
                kpis_layout += get_kpi_card_html("Inversión Total", f"${total_spend_curr:,.2f}", "Gasto total en pauta", total_spend_curr, total_spend_prev, lower_is_better=True) + "\n"
                kpis_layout += get_kpi_card_html("Impresiones Totales", f"{total_impressions_curr:,}", "Vistas acumuladas", total_impressions_curr, total_impressions_prev) + "\n"
                kpis_layout += get_kpi_card_html("Clics", f"{total_clicks_curr:,}", "Interacciones con anuncios", total_clicks_curr, total_clicks_prev) + "\n"
                kpis_layout += get_kpi_card_html("Costo por Conversión (CPA)", f"${cpa_curr:,.2f}", "Costo unitario", cpa_curr, cpa_prev, lower_is_better=True) + "\n"
                kpis_layout += get_kpi_card_html("CTR Promedio", f"{avg_ctr_curr:.2%}", "Tasa de clics/impresión", avg_ctr_curr, avg_ctr_prev) + "\n"
                kpis_layout += get_kpi_card_html("CPC Promedio", f"${avg_cpc_curr:,.2f}", "Costo promedio por clic", avg_cpc_curr, avg_cpc_prev, lower_is_better=True) + "\n"
                kpis_layout += '</div>'
            elif platform_type == "analytics":
                total_sessions_curr = df_curr["sessions"].sum()
                total_users_curr = df_curr["users"].sum()
                total_pageviews_curr = df_curr["pageviews"].sum()
                bounce_curr = df_curr["bounce_rate"].mean() if "bounce_rate" in df_curr.columns else 0.0
                
                total_sessions_prev = df_prev["sessions"].sum() if not df_prev.empty else 0.0
                total_users_prev = df_prev["users"].sum() if not df_prev.empty else 0.0
                total_pageviews_prev = df_prev["pageviews"].sum() if not df_prev.empty else 0.0
                bounce_prev = df_prev["bounce_rate"].mean() if (not df_prev.empty and "bounce_rate" in df_prev.columns) else 0.0
                
                kpis_layout = '<div class="kpis">\n'
                kpis_layout += get_kpi_card_html("Sesiones", f"{total_sessions_curr:,}", "Visitas al sitio web", total_sessions_curr, total_sessions_prev) + "\n"
                kpis_layout += get_kpi_card_html("Usuarios Activos", f"{total_users_curr:,}", "Visitantes únicos", total_users_curr, total_users_prev) + "\n"
                kpis_layout += get_kpi_card_html("Páginas Vistas", f"{total_pageviews_curr:,}", "Páginas cargadas", total_pageviews_curr, total_pageviews_prev) + "\n"
                kpis_layout += get_kpi_card_html("Tasa de Rebote", f"{bounce_curr:.2%}" if bounce_curr < 1.0 else f"{bounce_curr:.1f}%", "Porcentaje rebote", bounce_curr, bounce_prev, lower_is_better=True) + "\n"
                kpis_layout += '</div>'
            elif platform_type == "app_store":
                total_downloads_curr = df_curr["downloads"].sum()
                avg_rating_curr = df_curr["ratings"].mean() if "ratings" in df_curr.columns else 0.0
                
                total_downloads_prev = df_prev["downloads"].sum() if not df_prev.empty else 0.0
                avg_rating_prev = df_prev["ratings"].mean() if (not df_prev.empty and "ratings" in df_prev.columns) else 0.0
                
                kpis_layout = '<div class="kpis">\n'
                kpis_layout += get_kpi_card_html("Descargas", f"{total_downloads_curr:,}", "Descargas totales", total_downloads_curr, total_downloads_prev) + "\n"
                kpis_layout += get_kpi_card_html("Calificación Promedio", f"{avg_rating_curr:.2f}/5", "Puntuación tienda", avg_rating_curr, avg_rating_prev) + "\n"
                kpis_layout += '</div>'
            else:
                total_impressions_curr = df_curr["impressions"].sum()
                total_engagement_curr = df_curr["engagement"].sum()
                total_followers_curr = df_curr["followers"].max() if "followers" in df_curr.columns else 0.0
                total_reach_curr = df_curr["reach"].sum()
                
                total_impressions_prev = df_prev["impressions"].sum() if not df_prev.empty else 0.0
                total_engagement_prev = df_prev["engagement"].sum() if not df_prev.empty else 0.0
                total_followers_prev = df_prev["followers"].max() if (not df_prev.empty and "followers" in df_prev.columns) else 0.0
                total_reach_prev = df_prev["reach"].sum() if not df_prev.empty else 0.0
                
                kpis_layout = '<div class="kpis">\n'
                kpis_layout += get_kpi_card_html("Impresiones", f"{total_impressions_curr:,}", "Vistas de contenido", total_impressions_curr, total_impressions_prev) + "\n"
                kpis_layout += get_kpi_card_html("Interacciones (Engagement)", f"{total_engagement_curr:,}", "Reacciones/comentarios", total_engagement_curr, total_engagement_prev) + "\n"
                kpis_layout += get_kpi_card_html("Seguidores Totales", f"{total_followers_curr:,}", "Seguidores de la cuenta", total_followers_curr, total_followers_prev) + "\n"
                kpis_layout += get_kpi_card_html("Alcance Único", f"{total_reach_curr:,}", "Cuentas alcanzadas", total_reach_curr, total_reach_prev) + "\n"
                kpis_layout += '</div>'
                
            st.markdown(kpis_layout, unsafe_allow_html=True)
            
            # Historical charts
            st.markdown("### Tendencia Histórica e Indicadores")
            
            if "date" in df_curr.columns and not df_curr.empty:
                df_curr["date"] = pd.to_datetime(df_curr["date"])
                df_trend = df_curr.groupby(df_curr["date"].dt.date).agg({
                    "spend": "sum", "impressions": "sum", "clicks": "sum", "conversions": "sum", "reach": "sum",
                    "engagement": "sum", "followers": "max", "sessions": "sum", "users": "sum", "pageviews": "sum", "downloads": "sum"
                }).reset_index()
                
                df_trend["date"] = pd.to_datetime(df_trend["date"])
                df_trend = df_trend.sort_values("date")
                
                if not df_trend.empty:
                    col_metrics = st.columns(2)
                    with col_metrics[0]:
                        metric_left = st.selectbox(
                            "Métrica Eje Izquierdo",
                            options=[c for c in df_trend.columns if c != "date"],
                            index=0,
                            key="left_axis_selector"
                        )
                    with col_metrics[1]:
                        metric_right = st.selectbox(
                            "Métrica Eje Derecho",
                            options=[c for c in df_trend.columns if c != "date"],
                            index=min(1, len(df_trend.columns) - 2),
                            key="right_axis_selector"
                        )
                    
                    metric_left_label = next((item.get("display_name", metric_left) for item in metrics_list if item.get("name") == metric_left), metric_left)
                    metric_right_label = next((item.get("display_name", metric_right) for item in metrics_list if item.get("name") == metric_right), metric_right)
                    
                    # Dual Y Axis chart
                    base = alt.Chart(df_trend).encode(
                        x=alt.X('date:T', title='Fecha', axis=alt.Axis(format='%d/%m', labelColor='#8A97A8', titleColor='#8A97A8'))
                    )
                    
                    line_color_left = '#059669' if theme_mode == "light" else '#1AE08C'
                    line_color_right = '#4F46E5' if theme_mode == "light" else '#5C9DFF'
                    
                    line1 = base.mark_line(color=line_color_left, strokeWidth=3).encode(
                        y=alt.Y(f'{metric_left}:Q', title=metric_left_label, axis=alt.Axis(titleColor=line_color_left, labelColor=line_color_left))
                    )
                    
                    line2 = base.mark_line(color=line_color_right, strokeWidth=3).encode(
                        y=alt.Y(f'{metric_right}:Q', title=metric_right_label, axis=alt.Axis(titleColor=line_color_right, labelColor=line_color_right))
                    )
                    
                    chart_dual = alt.layer(line1, line2).resolve_scale(
                        y='independent'
                    ).properties(height=380).configure_view(strokeWidth=0).configure_axis(grid=False)
                    
                    st.altair_chart(chart_dual, use_container_width=True)
                else:
                    st.info("No hay suficientes puntos de fecha para construir la tendencia.")
            else:
                st.info("La dimensión temporal no está disponible en la consulta actual.")
                
            # Distribution of Conversions
            if not df_curr.empty and "campaign_name" in df_curr.columns:
                st.markdown("<br/>", unsafe_allow_html=True)
                if platform_type == "ads":
                    st.markdown("#### Distribución de Conversiones por Campaña")
                    df_camp = df_curr.groupby("campaign_name")["conversions"].sum().reset_index()
                    df_camp = df_camp.sort_values("conversions", ascending=False).head(10)
                    
                    chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
                        x=alt.X('conversions:Q', title='Conversiones'),
                        y=alt.Y('campaign_name:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
                    ).properties(height=350)
                    st.altair_chart(chart_camp, use_container_width=True)
                    
                elif platform_type == "analytics":
                    st.markdown("#### Sesiones por Campaña/Fuente")
                    df_camp = df_curr.groupby("campaign_name")["sessions"].sum().reset_index()
                    df_camp = df_camp.sort_values("sessions", ascending=False).head(10)
                    
                    chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
                        x=alt.X('sessions:Q', title='Sesiones'),
                        y=alt.Y('campaign_name:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
                    ).properties(height=350)
                    st.altair_chart(chart_camp, use_container_width=True)
                    
                else:
                    st.markdown("#### Alcance / Distribución por Publicación")
                    target_metric = "reach" if platform_type != "app_store" else "downloads"
                    df_camp = df_curr.groupby("campaign_name")[target_metric].sum().reset_index()
                    df_camp = df_camp.sort_values(target_metric, ascending=False).head(10)
                    
                    chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
                        x=alt.X(f"{target_metric}:Q", title='Alcance / Volumen'),
                        y=alt.Y('campaign_name:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
                    ).properties(height=350)
                    st.altair_chart(chart_camp, use_container_width=True)

            # CAMPAIGN BREAKDOWN TABLE
            st.markdown("### Detalle de Campañas y Resultados")
            df_table = df_curr.copy()

            group_keys = ["campaign_name", "platform"]
            for dim in selected_dimensions:
                if dim in df_table.columns and dim not in group_keys:
                    group_keys.append(dim)
                    
            if platform_type == "ads":
                df_table = df_table.groupby(group_keys).agg({
                    "spend": "sum", "impressions": "sum", "clicks": "sum", "conversions": "sum"
                }).reset_index()
                df_table["CTR"] = (df_table["clicks"] / df_table["impressions"]).apply(lambda x: f"{x:.2%}" if x > 0 else "0.00%")
                df_table["CPC"] = (df_table["spend"] / df_table["clicks"]).apply(lambda x: f"${x:,.2f}" if x > 0 else "$0.00")
                df_table["CPA"] = (df_table["spend"] / df_table["conversions"]).apply(lambda x: f"${x:,.2f}" if x > 0 else "$0.00")
                df_table["spend"] = df_table["spend"].apply(lambda x: f"${x:,.2f}")
                df_table["impressions"] = df_table["impressions"].apply(lambda x: f"{x:,}")
                df_table["clicks"] = df_table["clicks"].apply(lambda x: f"{x:,}")
                df_table["conversions"] = df_table["conversions"].apply(lambda x: f"{x:,}")
                df_table = df_table.rename(columns={"campaign_name": "Campaña", "platform": "Plataforma", "spend": "Inversión", "impressions": "Impresiones", "clicks": "Clics", "conversions": "Conversiones"})
            elif platform_type == "analytics":
                df_table = df_table.groupby(group_keys).agg({
                    "sessions": "sum", "users": "sum", "pageviews": "sum"
                }).reset_index()
                df_table["sessions"] = df_table["sessions"].apply(lambda x: f"{x:,}")
                df_table["users"] = df_table["users"].apply(lambda x: f"{x:,}")
                df_table["pageviews"] = df_table["pageviews"].apply(lambda x: f"{x:,}")
                df_table = df_table.rename(columns={"campaign_name": "Dimensión/Campaña", "platform": "Plataforma", "sessions": "Sesiones", "users": "Usuarios", "pageviews": "Páginas Vistas"})
            else:
                df_table = df_table.groupby(group_keys).agg({
                    "impressions": "sum", "engagement": "sum", "reach": "sum"
                }).reset_index()
                df_table["impressions"] = df_table["impressions"].apply(lambda x: f"{x:,}")
                df_table["engagement"] = df_table["engagement"].apply(lambda x: f"{x:,}")
                df_table["reach"] = df_table["reach"].apply(lambda x: f"{x:,}")
                df_table = df_table.rename(columns={"campaign_name": "Publicación", "platform": "Plataforma", "impressions": "Impresiones", "engagement": "Interacciones", "reach": "Alcance"})
                
            st.dataframe(df_table, width="stretch", hide_index=True)

        if is_meta:
            with tab_featured:
                st.markdown("### Desempeño de Campañas Destacadas")
                st.markdown(get_featured_campaigns_table_html(theme_mode), unsafe_allow_html=True)
                st.markdown("<br/>", unsafe_allow_html=True)
                
                # Render Demographics Section if selected
                st.markdown("### Datos Demográficos de Audiencia")
                load_demographics = st.checkbox("Cargar data de desglose oficial Facebook Ads (Edad/Sexo)", value=False)
                
                if load_demographics:
                    with st.spinner("Cargando data de desglose de Facebook..."):
                        demo_metrics = ["impressions", "reach", "clicks", "conversions"]
                        demo_dimensions = ["age", "gender", "date"]
                        
                        demo_curr_data = fetch_campaign_data_from_api(
                            platform_key, client_id, user_id, account_id,
                            start_date, end_date, demo_metrics, demo_dimensions,
                            opt_filters, False, api_key, show_errors=False
                        )
                        
                        if demo_curr_data:
                            df_demo = process_api_response(demo_curr_data, platform_key, client_id, user_id)
                            
                            # Clean up Age and Gender
                            def ensure_breakdown_column(df, column):
                                if column not in df.columns:
                                    df[column] = "Desconocido"
                                df[column] = df[column].fillna("Desconocido")
                                return df
                            
                            df_demo = ensure_breakdown_column(df_demo, "age")
                            df_demo = ensure_breakdown_column(df_demo, "gender")
                            
                            # Aggregate by Age and Gender
                            df_age_gender = df_demo.groupby(["age", "gender"])["impressions"].sum().reset_index()
                            
                            # Draw demographics bar chart
                            demo_chart = alt.Chart(df_age_gender).mark_bar().encode(
                                x=alt.X("impressions:Q", title="Impresiones"),
                                y=alt.Y("age:N", title="Rango de Edad"),
                                color=alt.Color("gender:N", scale=alt.Scale(
                                    domain=["Masculino", "Femenino", "Desconocido"],
                                    range=["#5C9DFF", "#FF6B6B", "#8A97A8"]
                                ), title="Sexo"),
                                row=alt.Row("gender:N", title=None)
                            ).properties(height=180, width=600)
                            
                            st.altair_chart(demo_chart, use_container_width=True)
                            
                            # Region breakdown table
                            st.markdown("#### Distribución de Impresiones por Región")
                            region_curr_data = fetch_campaign_data_from_api(
                                platform_key, client_id, user_id, account_id,
                                start_date, end_date, ["impressions"], ["region"],
                                opt_filters, False, api_key, show_errors=False
                            )
                            if region_curr_data:
                                df_region = process_api_response(region_curr_data, platform_key, client_id, user_id)
                                if "region" in df_region.columns:
                                    df_region_agg = df_region.groupby("region")["impressions"].sum().reset_index()
                                    df_region_agg = df_region_agg.sort_values("impressions", ascending=False).head(10)
                                    df_region_agg["impressions"] = df_region_agg["impressions"].apply(lambda x: f"{x:,}")
                                    st.dataframe(df_region_agg.rename(columns={"region": "Región", "impressions": "Impresiones"}), hide_index=True, width="stretch")
                                else:
                                    st.info("No se devolvió la columna 'region' en la consulta.")
                            else:
                                st.info("No hay desglose regional disponible para este rango.")
                        else:
                            st.info("No se pudo obtener el desglose demográfico para esta cuenta en el periodo seleccionado.")

            with tab_content:
                st.markdown("### Ranking: Top Posts por Engagement (Facebook)")
                facebook_posts = [
                    {
                        "author": "Nutri",
                        "time": "Hace aprox. 2 meses",
                        "body": "Cuando necesitas algo práctico y con sabor a fruta...",
                        "image": "https://images.unsplash.com/photo-1613478223719-2ab802602423?auto=format&fit=crop&w=400&q=80",
                        "engagement": "16.51%",
                        "reactions": "521"
                    },
                    {
                        "author": "Nutri",
                        "time": "Hace aprox. 2 meses",
                        "body": "Atención 👀 Verifica que eres un verdadero fan de Nutri...",
                        "image": "https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=400&q=80",
                        "engagement": "15.00%",
                        "reactions": "701"
                    },
                    {
                        "author": "Nutri",
                        "time": "Hace aprox. 3 meses",
                        "body": "Houston... parece que alguien llegó hasta la luna...",
                        "image": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=400&q=80",
                        "engagement": "13.76%",
                        "reactions": "859"
                    },
                    {
                        "author": "Nutri",
                        "time": "Hace aprox. 3 meses",
                        "body": "Los pendientes pueden esperar... pero tu break no 😜 Porque...",
                        "image": "https://images.unsplash.com/photo-1570042225831-d98fa7577f1e?auto=format&fit=crop&w=400&q=80",
                        "engagement": "10.22%",
                        "reactions": "2,969"
                    }
                ]
                
                post_cols = st.columns(4)
                for idx, post in enumerate(facebook_posts):
                    card_html = f"""
                    <div class="post-card">
                        <div class="post-badge">#{idx+1}</div>
                        <div class="post-header">
                            <div class="post-avatar">N</div>
                            <div>
                                <div class="post-author">{post['author']}</div>
                                <div class="post-time">{post['time']}</div>
                            </div>
                        </div>
                        <div class="post-body">{post['body']}</div>
                        <img class="post-image" src="{post['image']}" alt="Post media">
                        <div class="post-footer">
                            <div>
                                <div class="post-metric-label">Engagement</div>
                                <div class="post-metric-value">{post['engagement']}</div>
                            </div>
                            <div style="text-align: right;">
                                <div class="post-metric-label">Reacciones</div>
                                <div class="post-metric-value">{post['reactions']}</div>
                            </div>
                        </div>
                    </div>
                    """
                    with post_cols[idx]:
                        st.markdown(card_html, unsafe_allow_html=True)
                
                st.markdown("<br/><br/>", unsafe_allow_html=True)
                st.markdown("### Ranking de Reels por Engagement (Facebook Videos Verticales)")
                reels_data = [
                    {
                        "body": "Hay lugares que no solo se visitan... se sienten 🧡",
                        "image": "https://images.unsplash.com/photo-1531403009284-440f080d1e12?auto=format&fit=crop&w=400&q=80",
                        "engagement": "3.03%",
                        "plays": "2,214",
                        "reach": "2,181",
                        "likes": "57"
                    },
                    {
                        "body": "Todo empezó con una coincidencia...",
                        "image": "https://images.unsplash.com/photo-1611080626919-7cf5a9dbab5b?auto=format&fit=crop&w=400&q=80",
                        "engagement": "0.05%",
                        "plays": "90.51k",
                        "reach": "320.41k",
                        "likes": "149"
                    },
                    {
                        "body": "El bienestar en el trabajo no solo depende de las...",
                        "image": "https://images.unsplash.com/photo-1531403009284-440f080d1e12?auto=format&fit=crop&w=400&q=80",
                        "engagement": "0.04%",
                        "plays": "39.91k",
                        "reach": "97.13k",
                        "likes": "36"
                    }
                ]
                
                reel_cols = st.columns(3)
                for idx, reel in enumerate(reels_data):
                    card_html = f"""
                    <div class="post-card">
                        <div class="post-badge">#{idx+1}</div>
                        <div class="reel-image" style="background-image: url('{reel['image']}'); background-size: cover; background-position: center;">
                            <div class="play-btn">▶</div>
                        </div>
                        <div class="post-body" style="font-weight: 700;">{reel['body']}</div>
                        <div class="post-footer" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; border-top: 1px solid rgba(128,128,128,0.15); padding-top: 10px;">
                            <div style="border-bottom: 1px dashed rgba(128,128,128,0.15); padding-bottom: 5px;">
                                <span class="post-metric-label">Engagement</span><br/>
                                <b class="post-metric-value">{reel['engagement']}</b>
                            </div>
                            <div style="border-bottom: 1px dashed rgba(128,128,128,0.15); padding-bottom: 5px; text-align: right;">
                                <span class="post-metric-label">Reproducciones</span><br/>
                                <b class="post-metric-value">{reel['plays']}</b>
                            </div>
                            <div>
                                <span class="post-metric-label">Alcance Único</span><br/>
                                <b class="post-metric-value">{reel['reach']}</b>
                            </div>
                            <div style="text-align: right;">
                                <span class="post-metric-label">Me Gusta</span><br/>
                                <b class="post-metric-value">{reel['likes']}</b>
                            </div>
                        </div>
                    </div>
                    """
                    with reel_cols[idx]:
                        st.markdown(card_html, unsafe_allow_html=True)
                        
                st.markdown("<br/><br/>", unsafe_allow_html=True)
                st.markdown("### Ranking de Hashtags (Instagram)")
                st.markdown(get_hashtags_table_html(theme_mode), unsafe_allow_html=True)
