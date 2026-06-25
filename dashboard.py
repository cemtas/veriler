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

# --- GÖRSEL OKUYUCU (Base64) ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return None

filigran_b64 = get_base64_of_bin_file("filigran.png")
if not filigran_b64: filigran_b64 = get_base64_of_bin_file("filigran.jpg")

# --- STİL VE CSS AYARLARI ---
filigran_html = f"""
<style>@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&display=swap');</style>
<div class="watermark-bg"></div>
<style>
.watermark-bg {{ position: fixed; top: 50%; left: 50%; width: 100vw; height: 100vh; transform: translate(-50%, -50%); background-image: url("data:image/png;base64,{filigran_b64}"); background-size: 25%; background-position: center; background-repeat: no-repeat; opacity: 0.65; z-index: 0; pointer-events: none; }}
</style>
""" if filigran_b64 else "<style>@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&display=swap');</style>"
st.markdown(filigran_html, unsafe_allow_html=True)

st.markdown("""
<style>
header {visibility: hidden; height: 0px !important;}
footer {visibility: hidden; height: 0px !important;}
.block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; margin-top: -30px; max-width: 98% !important; position: relative; z-index: 10; }
[data-testid="stAppViewContainer"] { background-color: #050810; overflow: hidden; } 

/* BUZLU CAM EFEKTİ DÜZELTİLDİ (Daha şeffaf, filigran daha net) */
.metric-card, .ref-card { background: rgba(10, 15, 25, 0.25); backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); border: 1px solid rgba(255, 255, 255, 0.3); box-shadow: 0 4px 10px 0 rgba(0, 0, 0, 0.3); border-radius: 12px; text-align: center; position: relative; z-index: 10; transition: all 0.3s ease; }
.metric-card { padding: 5px; margin-bottom: 0px; }
.metric-title { font-size: 24px; color: #ffffff; font-weight: 700; text-transform: uppercase; margin-bottom: 0px; letter-spacing: 1px; }
.metric-value { font-size: 50px; font-weight: bold; color: #ffffff; line-height: 1.1; text-shadow: 0px 2px 4px rgba(0,0,0,0.8); }
.ref-card { padding: 5px; border-radius: 12px; }
.ref-title { color: #ffffff; font-size: 20px; font-weight: 600; margin-bottom: 0px; }
.ref-value { font-size: 34px; font-weight: bold; color: #fff; line-height: 1.1; text-shadow: 0px 2px 4px rgba(0,0,0,0.8); }

@keyframes blink-green { 0% { border-color: rgba(76,175,80,0.5); box-shadow: 0 0 5px rgba(76,175,80,0.5); } 50% { border-color: #4caf50; background: rgba(76, 175, 80, 0.2); box-shadow: 0 0 30px rgba(76,175,80,0.8); } 100% { border-color: rgba(76,175,80,0.5); box-shadow: 0 0 5px rgba(76,175,80,0.5); } }
.alarm-up { animation: blink-green 1.5s infinite !important; }
@keyframes blink-red { 0% { border-color: rgba(239,83,80,0.5); box-shadow: 0 0 5px rgba(239,83,80,0.5); } 50% { border-color: #ef5350; background: rgba(239, 83, 80, 0.2); box-shadow: 0 0 30px rgba(239,83,80,0.8); } 100% { border-color: rgba(239,83,80,0.5); box-shadow: 0 0 5px rgba(239,83,80,0.5); } }
.alarm-down { animation: blink-red 1.5s infinite !important; }

/* KAYAN YAZI */
.marquee-container { position: fixed; bottom: 0; left: 0; width: 100%; height: 38px; background-color: rgba(5, 8, 15, 0.98); border-top: 2px solid #4ade80; z-index: 9999; display: flex; align-items: center; overflow: hidden; }
.marquee-content { width: 100%; color: #4ade80; font-size: 22px; font-weight: 600; letter-spacing: 1px; }
.marquee-item { margin-right: 50px; }
.marquee-item b { color: #ffffff; font-weight: 700; margin-right: 8px; }

div[data-testid="stVerticalBlock"] > div { padding-bottom: 0.1rem !important; }
</style>
""", unsafe_allow_html=True)

# --- VERİ İŞLEME VE FORMATLAMA ---
def get_ingilizce_tarih():
    gunler_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    now = datetime.datetime.now()
    return f"{now.strftime('%d.%m.%Y')} / {gunler_en[now.weekday()]}"

def format_tamsayi(deger, sembol=""):
    try:
        if deger != deger or deger is None or deger == 0: return f"{sembol} 0".strip()
        # Tam sayıya yuvarlayıp binlik ayraç olarak virgül koyar, sonra onu noktaya çevirir
        return f"{sembol} {int(round(float(deger))):,}".replace(",", ".").strip()
    except: return f"{sembol} 0".strip()

def format_ondalik(deger, sembol=""):
    try:
        if deger != deger or deger is None or deger == 0: return f"{sembol} 0.00".strip()
        return f"{sembol} {deger:.2f}".strip()
    except: return f"{sembol} 0.00".strip()

# --- M-1 VERİ ÇEKME FONKSİYONU (CACHE KIRICI İSİM V5) ---
@st.cache_data(ttl=3600)
def gecmis_ay_verileri_v5():
    now = datetime.datetime.now()
    son_gun = now.replace(day=1) - datetime.timedelta(days=1)
    ilk_gun = son_gun.replace(day=1)
    m1_data = { "LME($)(M-1)": 2485.20, "LME(€)(M-1)": 2310.50, "MB($)(M-1)": 2510.00 }
    
    try:
        bitis_gunu = son_gun + datetime.timedelta(days=1)
        lme_hist = yf.Ticker("ALI=F").history(start=ilk_gun.strftime('%Y-%m-%d'), end=bitis_gunu.strftime('%Y-%m-%d'))
        parite_hist = yf.Ticker("EURUSD=X").history(start=ilk_gun.strftime('%Y-%m-%d'), end=bitis_gunu.strftime('%Y-%m-%d'))
        if not lme_hist.empty: 
            ort = lme_hist['Close'].mean()
            if ort == ort and ort > 0: m1_data["LME($)(M-1)"] = float(ort)
        if not lme_hist.empty and not parite_hist.empty: 
            p_ort = parite_hist['Close'].mean()
            if p_ort == p_ort and p_ort > 0: m1_data["LME(€)(M-1)"] = m1_data["LME($)(M-1)"] / float(p_ort)
    except: pass

    try:
        gecen_ay = now - relativedelta(months=1)
        aylar_en = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        ay_isim_en = aylar_en[gecen_ay.month - 1]
        hedef_url = f"https://metalradar.com/price/duty-paid-european-aluminium-premium/lme/{ay_isim_en}-{gecen_ay.year}-forward/indicative-ask"
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
        res = scraper.get(hedef_url, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            cek_fiyat = 0.0
            for tag in soup.find_all(['span', 'div', 'p', 'h1', 'h2', 'h3']):
                if tag.get('class'):
                    siniflar = " ".join(tag.get('class')).lower()
                    if 'price' in siniflar or 'premium' in siniflar or 'value' in siniflar:
                        temiz_deger = re.sub(r'[^0-9.]', '', tag.text)
                        if temiz_deger:
                            try:
                                fiyat = float(temiz_deger)
                                if 100 < fiyat < 5000: 
                                    cek_fiyat = fiyat
                                    break
                            except: pass
            if cek_fiyat == 0.0:
                matches = re.findall(r'\$\s*([0-9]{3,4}(?:\.[0-9]{1,2})?)', soup.get_text())
                if matches: cek_fiyat = float(matches[0])
            if cek_fiyat > 0: m1_data["MB($)(M-1)"] = cek_fiyat
    except: pass
    return m1_data

# --- CANLI VERİ VE ALT BANT ÇEKME (CACHE KIRICI İSİM V5) ---
@st.cache_data(ttl=60)
def anlik_piyasa_verileri_v5():
    veri_paketi = {
        "LME Aluminium ($)": {"val": 0.0, "durum": "normal"}, "LME Aluminium (€)": {"val": 0.0, "durum": "normal"},
        "Metal Bulletin ($)": {"val": 0.0, "durum": "normal"}, "USD/TL": {"val": 0.0, "durum": "normal"},
        "EURO/TL": {"val": 0.0, "durum": "normal"}, "PARİTE (EURO/USD)": {"val": 0.0, "durum": "normal"}
    }
    alt_bant = { "ONS": 0.0, "BTC": 0.0, "BIST": 0.0, "BRENT": 0.0, "GRAM": 0.0 }
    alarm_limiti = 1.5 
    
    def alarm_hesapla(guncel, onceki):
        if onceki == 0 or onceki is None: return "normal"
        degisim = ((guncel - onceki) / onceki) * 100
        if degisim >= alarm_limiti: return "alarm_up"
        if degisim <= -alarm_limiti: return "alarm_down"
        return "normal"
    
    def get_data_safe(ticker, inv_url, is_tr):
        val, prev = 0.0, 0.0
        
        try:
            if ticker:
                tkr = yf.Ticker(ticker)
                hist = tkr.history(period="5d")
                if len(hist) > 1: prev = float(hist['Close'].iloc[-2])
                elif len(hist) == 1: prev = float(hist['Close'].iloc[0])
        except: pass
        
        try:
            if inv_url:
                scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
                res = scraper.get(inv_url, timeout=5)
                if res.status_code == 200:
                    match = re.search(r'data-test="instrument-price-last"[^>]*>([\d\.,]+)', res.text)
                    if not match: match = re.search(r'class="text-5xl[^>]*>([\d\.,]+)', res.text)
                    if match:
                        v_str = match.group(1)
                        if is_tr: v_str = v_str.replace('.', '').replace(',', '.')
                        else: v_str = v_str.replace(',', '')
                        val = float(re.sub(r'[^0-9.]', '', v_str))
        except: pass
        
        if val == 0.0 and ticker:
            try:
                tkr = yf.Ticker(ticker)
                p = tkr.fastinfo.last_price
                if p and p > 0: val = float(p)
                else:
                    hist = tkr.history(period="2d")
                    if not hist.empty: val = float(hist['Close'].iloc[-1])
            except: pass
            
        return val, prev

    usd_g, usd_o = get_data_safe("TRY=X", "https://tr.investing.com/currencies/usd-try", True)
    if usd_g > 0:
        veri_paketi["USD/TL"]["val"] = usd_g
        veri_paketi["USD/TL"]["durum"] = alarm_hesapla(usd_g, usd_o)

    eur_g, eur_o = get_data_safe("EURTRY=X", "https://tr.investing.com/currencies/eur-try", True)
    if eur_g > 0:
        veri_paketi["EURO/TL"]["val"] = eur_g
        veri_paketi["EURO/TL"]["durum"] = alarm_hesapla(eur_g, eur_o)

    lme_g, lme_o = get_data_safe("ALI=F", "https://www.investing.com/commodities/aluminum", False)
    if lme_g > 0:
        veri_paketi["LME Aluminium ($)"]["val"] = lme_g
        veri_paketi["LME Aluminium ($)"]["durum"] = alarm_hesapla(lme_g, lme_o)

    p_guncel, p_onceki = get_data_safe("EURUSD=X", None, False)
    if p_guncel > 0:
        veri_paketi["PARİTE (EURO/USD)"]["val"] = p_guncel
        veri_paketi["PARİTE (EURO/USD)"]["durum"] = alarm_hesapla(p_guncel, p_onceki)

    if veri_paketi["PARİTE (EURO/USD)"]["val"] > 0 and veri_paketi["LME Aluminium ($)"]["val"] > 0: 
        veri_paketi["LME Aluminium (€)"]["val"] = veri_paketi["LME Aluminium ($)"]["val"] / veri_paketi["PARİTE (EURO/USD)"]["val"]
        veri_paketi["LME Aluminium (€)"]["durum"] = veri_paketi["LME Aluminium ($)"]["durum"]
    
    try:
        payload = {"symbols": {"tickers": ["COMEX:EDP1!"]}, "columns": ["close"]}
        for endpoint in ["america", "global", "futures"]:
            try:
                tv_res = requests.post(f"https://scanner.tradingview.com/{endpoint}/scan", json=payload, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                if tv_res.status_code == 200: 
                    tv_data = tv_res.json()
                    if 'data' in tv_data and len(tv_data['data']) > 0:
                        veri_paketi["Metal Bulletin ($)"]["val"] = float(tv_data['data'][0]['d'][0])
                        break
            except: continue
    except: pass

    alt_bant["BTC"], _ = get_data_safe("BTC-USD", None, False)
    alt_bant["BIST"], _ = get_data_safe("XU100.IS", None, False)
    alt_bant["BRENT"], _ = get_data_safe("BZ=F", None, False)
    alt_bant["ONS"], _ = get_data_safe("XAUUSD=X", "https://tr.investing.com/currencies/xau-usd", True)
    
    gram_g, _ = get_data_safe(None, "https://tr.investing.com/currencies/gau-try", True)
    if gram_g > 0: 
        alt_bant["GRAM"] = gram_g
    elif alt_bant["ONS"] > 0 and veri_paketi["USD/TL"]["val"] > 0:
        alt_bant["GRAM"] = (alt_bant["ONS"] / 31.1034768) * veri_paketi["USD/TL"]["val"]

    return veri_paketi, alt_bant

veriler, alt_bant_verileri = anlik_piyasa_verileri_v5()
m1_veriler = gecmis_ay_verileri_v5()

# --- ARAYÜZ OLUŞTURMA ---
top_empty = st.empty()
with top_empty.container():
    now = datetime.datetime.now()
    # Tarih ve saat ikisi de neon yeşil (#4ade80)
    ust_panel_html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 15px; margin-bottom: 10px;">
        <div style="font-family: 'Orbitron', sans-serif; font-size: 38px; color: #4ade80; font-weight: 700; text-shadow: 0px 0px 10px rgba(74,222,128,0.4);">{get_ingilizce_tarih()}</div>
        <div style="font-family: 'Orbitron', sans-serif; font-size: 46px; color: #4ade80; font-weight: 700; letter-spacing: 3px; line-height: 0.8; text-shadow: 0px 0px 10px rgba(74,222,128,0.4);">{now.strftime('%H:%M')}</div>
    </div>
    """
    st.markdown(ust_panel_html, unsafe_allow_html=True)

st.markdown("<h3 style='color: #00ffff; font-size: 34px; margin-bottom: 5px; margin-top: 0; text-align: center; position: relative; z-index: 10; font-weight: 900; letter-spacing: 2px; text-shadow: 0px 0px 10px rgba(0,255,255,0.5), 0px 4px 15px rgba(0,0,0,0.9);'>LIVE MARKET DATA</h3>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
def kart(baslik, deger, durum): 
    css_class = f"metric-card {durum if durum != 'normal' else ''}"
    return f"""<div class="{css_class}"><div class="metric-title">{baslik}</div><div class="metric-value">{deger}</div></div>"""

with col1:
    st.markdown(kart("LME Aluminium ($)", format_tamsayi(veriler['LME Aluminium ($)']['val'], "$"), veriler['LME Aluminium ($)']['durum']), unsafe_allow_html=True)
    st.markdown(kart("USD/TL", format_ondalik(veriler['USD/TL']['val'], "₺"), veriler['USD/TL']['durum']), unsafe_allow_html=True)
with col2:
    st.markdown(kart("LME Aluminium (€)", format_tamsayi(veriler['LME Aluminium (€)']['val'], "€"), veriler['LME Aluminium (€)']['durum']), unsafe_allow_html=True)
    st.markdown(kart("EURO/TL", format_ondalik(veriler['EURO/TL']['val'], "₺"), veriler['EURO/TL']['durum']), unsafe_allow_html=True)
with col3:
    st.markdown(kart("Metal Bulletin ($)", format_tamsayi(veriler['Metal Bulletin ($)']['val'], "$"), veriler['Metal Bulletin ($)']['durum']), unsafe_allow_html=True)
    st.markdown(kart("PARİTE (EURO/USD)", format_ondalik(veriler['PARİTE (EURO/USD)']['val']), veriler['PARİTE (EURO/USD)']['durum']), unsafe_allow_html=True)

st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 5px 0; position: relative; z-index: 10;'>", unsafe_allow_html=True)

st.markdown("<h3 style='color: #00ffff; font-size: 34px; margin-bottom: 5px; margin-top: 0; text-align: center; position: relative; z-index: 10; font-weight: 900; letter-spacing: 2px; text-shadow: 0px 0px 10px rgba(0,255,255,0.5), 0px 4px 15px rgba(0,0,0,0.9);'>AVERAGE (M-1)</h3>", unsafe_allow_html=True)

m_col1, m_col2, m_col3 = st.columns(3)
def ref(baslik, deger): return f"""<div class='ref-card'><div class='ref-title'>{baslik}</div><div class='ref-value'>{deger}</div></div>"""

with m_col1: st.markdown(ref("LME($)(M-1)", format_tamsayi(m1_veriler['LME($)(M-1)'], "$")), unsafe_allow_html=True)
with m_col2: st.markdown(ref("LME(€)(M-1)", format_tamsayi(m1_veriler['LME(€)(M-1)'], "€")), unsafe_allow_html=True)
with m_col3: st.markdown(ref("MB($)(M-1)", format_tamsayi(m1_veriler['MB($)(M-1)'], "$")), unsafe_allow_html=True)

imza_html = """
<div style="text-align: center; margin-top: 15px; margin-bottom: 60px; position: relative; z-index: 10;">
    <span style="font-family: 'Segoe UI Light', 'Helvetica Neue', Arial, sans-serif; font-size: 22px; font-weight: 500; color: #cbd5e1; letter-spacing: 3px; text-shadow: 0px 1px 3px rgba(0,0,0,0.8);">Powered by Cem TAŞ | Copyright © | canliveriler 2.0</span>
</div>
"""
st.markdown(imza_html, unsafe_allow_html=True)

# TAM SAYI (KÜSÜRATSIZ) VE NOKTALI KAYAN YAZI BANDI
kayan_str = (
    f"<div class='marquee-container'><marquee class='marquee-content' scrollamount='8'>"
    f"<span class='marquee-item'><b>GRAM ALTIN (GAU):</b> {format_tamsayi(alt_bant_verileri['GRAM'], '₺')}</span>"
    f"<span class='marquee-item'><b>ONS ALTIN (XAU):</b> {format_tamsayi(alt_bant_verileri['ONS'], '$')}</span>"
    f"<span class='marquee-item'><b>BİTCOİN (₿):</b> {format_tamsayi(alt_bant_verileri['BTC'], '$')}</span>"
    f"<span class='marquee-item'><b>BIST100 (XU100):</b> {format_tamsayi(alt_bant_verileri['BIST'])}</span>"
    f"<span class='marquee-item'><b>BRENT (LCOU6):</b> {format_tamsayi(alt_bant_verileri['BRENT'], '$')}</span>"
    f"</marquee></div>"
)
st.write(kayan_str, unsafe_allow_html=True)

time.sleep(2)
st.rerun()
