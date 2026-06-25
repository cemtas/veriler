import streamlit as st
import datetime
import time
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
import cloudscraper
import re
import base64

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Canlı Takip Dashboard", page_icon="mrp_ikon.ico", layout="wide", initial_sidebar_state="collapsed")

# --- CSS VE TASARIM ---
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #050810; overflow: hidden; }
/* Sıkıştırılmış layout */
.block-container { padding-top: 5px !important; padding-bottom: 5px !important; }
.metric-card { background: rgba(10, 15, 25, 0.4); border: 1px solid rgba(255,255,255,0.2); border-radius: 10px; text-align: center; padding: 5px; }
.metric-title { font-size: 16px; color: #a0aec0; }
.metric-value { font-size: 32px; font-weight: bold; color: #ffffff; }
.marquee-container { position: fixed; bottom: 0; width: 100%; background: #0a0f19; color: #4ade80; font-size: 18px; padding: 5px; border-top: 1px solid #4ade80; }
.scroll-indicator { color: #00ffff; font-size: 16px; text-align: center; margin: 5px 0; cursor: pointer; }
</style>
""", unsafe_allow_html=True)

# --- VERİ ÇEKME ---
def get_live_data():
    data = {"USD/TL": 0.0, "EUR/TL": 0.0, "GRAM": 0.0, "ONS": 0.0, "BTC": 0.0, "BIST": 0.0, "BRENT": 0.0}
    headers = {"User-Agent": "Mozilla/5.0"}
    urls = {
        "USD/TL": "https://tr.investing.com/currencies/usd-try",
        "EUR/TL": "https://tr.investing.com/currencies/eur-try",
        "GRAM": "https://tr.investing.com/currencies/gau-try",
        "ONS": "https://tr.investing.com/currencies/xau-usd"
    }
    for key, url in urls.items():
        try:
            res = requests.get(url, headers=headers, timeout=5)
            match = re.search(r'data-test="instrument-price-last"[^>]*>([\d\.,]+)', res.text)
            if match:
                data[key] = float(match.group(1).replace('.', '').replace(',', '.'))
        except: pass
    
    # Kalan veriler
    try:
        data["BTC"] = float(yf.Ticker("BTC-USD").fastinfo.last_price)
        data["BIST"] = float(yf.Ticker("XU100.IS").fastinfo.last_price)
        data["BRENT"] = float(yf.Ticker("BZ=F").fastinfo.last_price)
    except: pass
    return data

vals = get_live_data()

# --- HEADER (Tarih - Saat Tek Satır) ---
now = datetime.datetime.now()
st.markdown(f"""
<div style='text-align:center; color:#4ade80; font-family: Orbitron; font-size: 28px; margin-bottom:10px;'>
    {now.strftime('%d.%m.%Y')} | {now.strftime('%H:%M')}
</div>
""", unsafe_allow_html=True)

# Başlık
st.markdown("<h3 style='color:#00ffff; text-align:center;'>LIVE MARKET DATA</h3>", unsafe_allow_html=True)

# Kartlar (Sıkıştırılmış)
cols = st.columns(4)
cols[0].markdown(f"<div class='metric-card'><div class='metric-title'>USD/TL</div><div class='metric-value'>₺{vals['USD/TL']:.2f}</div></div>", unsafe_allow_html=True)
cols[1].markdown(f"<div class='metric-card'><div class='metric-title'>EUR/TL</div><div class='metric-value'>₺{vals['EUR/TL']:.2f}</div></div>", unsafe_allow_html=True)
cols[2].markdown(f"<div class='metric-card'><div class='metric-title'>GRAM GAU</div><div class='metric-value'>₺{vals['GRAM']:,.0f}</div></div>", unsafe_allow_html=True)
cols[3].markdown(f"<div class='metric-card'><div class='metric-title'>ONS XAU</div><div class='metric-value'>${vals['ONS']:,.0f}</div></div>", unsafe_allow_html=True)

# Scroll Uyarısı (Düzenlendi)
st.markdown("<div class='scroll-indicator'>▼ SCROLL FOR AVERAGE (M-1) ▼</div>", unsafe_allow_html=True)

# İmza
st.markdown("<div style='text-align:center; color:#cbd5e1; margin-top:10px;'>Powered by Cem TAŞ</div>", unsafe_allow_html=True)

# Kayan Yazı
st.markdown(f"""
<div class='marquee-container'>
    <marquee> GRAM (GAU): ₺{vals['GRAM']:,.0f} | ONS (XAU): ${vals['ONS']:,.0f} | BİTCOİN: ${vals['BTC']:,.0f} | BIST100: {vals['BIST']:,.0f} | BRENT: ${vals['BRENT']:.2f} </marquee>
</div>
""", unsafe_allow_html=True)

time.sleep(2)
st.rerun()
