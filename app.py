import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="BIST Pro Terminal", layout="wide")

# --- 1. GÜNCEL BIST 100 LİSTESİ ---
def bist_listesi_getir():
    bist100 = [
        "AEFES", "AGHOL", "AKBNK", "AKCNS", "AKFGY", "AKSA", "AKSEN", "ALARK", "ALFAS", "ARCLK",
        "ASELS", "ASTOR", "ASUZU", "AYDEM", "BAGFS", "BERA", "BIENP", "BIMAS", "BRSAN", "BRYAT",
        "BUCIM", "CANTE", "CCOLA", "CIMSA", "CWENE", "DOAS", "DOHOL", "EGEEN", "EKGYO", "ENJSA",
        "ENKAI", "EREGL", "EUPWR", "EUREN", "FROTO", "GARAN", "GENIL", "GESAN", "GUBRF",
        "GWIND", "HALKB", "HEKTS", "IPEKE", "ISCTR", "ISGYO", "IZENR", "KARDM", "KAYSE", "KCHOL",
        "KLRGY", "KOCAER", "KONTR", "KONYA", "KORDS", "KOZAA", "KOZAL", "KRDMD", "MAVI", "MHRGY",
        "MIATK", "MPARK", "ODAS", "OTKAR", "OYAKC", "PENTA", "PETKM", "PGSUS", "QUAGR", "REEDR",
        "SAHOL", "SASA", "SAYAS", "SDTTR", "SISE", "SKBNK", "SMRTG", "SNGYO", "SOKM", "TABGD",
        "TARKN", "TAVHL", "TCELL", "THYAO", "TKFEN", "TMSN", "TOASO", "TSKB", "TTKOM", "TUPRS",
        "TURSG", "ULKER", "VAKBN", "VESBE", "VESTL", "YEOTK", "YKBNK", "YYLGD", "ZOREN"
    ]
    return [h + ".IS" for h in sorted(bist100)]

# --- 2. ANALİZ MOTORU (RESAMPLING & FIBONACCI) ---
def analiz_et(ticker, periyot):
    # Yahoo'nun anlayacağı temel interval ve period ayarları
    if periyot in ["2 Saat", "4 Saat"]:
        interval = "1h"
        data_period = "730d"
    elif periyot == "Günlük":
        interval = "1d"
        data_period = "2y"
    else: # Haftalık ve Aylık
        interval = "1wk" if periyot == "Haftalık" else "1mo"
        data_period = "max"
    
    try:
        df = yf.download(ticker, period=data_period, interval=interval, progress=False, auto_adjust=True)
        if df.empty or len(df) < 35: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # --- SAATLİK VERİLERİ BİRLEŞTİRME (RESAMPLING) ---
        if periyot == "2 Saat":
            df = df.resample('2h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
        elif periyot == "4 Saat":
            df = df.resample('4h').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()

        # İndikatörler
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)

        # Fibonacci Seviyeleri (Önceki Bar)
        last_h, last_l, last_c = df['High'].iloc[-2], df['Low'].iloc[-2], df['Close'].iloc[-2]
        pivot = (last_h + last_l + last_c) / 3
        diff = last_h - last_l
        r2 = pivot + (0.618 * diff)
        s2 = pivot - (0.618 * diff)
        
        current_c = float(df['Close'].iloc[-1])

        # Düşeni Kıran (Trend Breakout)
        lookback = 20
        y = df['High'].tail(lookback).values
        x = np.arange(lookback)
        slope, intercept = np.polyfit(x, y, 1)
        trend_line = slope * lookback + intercept
        kirilim = "✅ KIRILDI" if (slope < 0 and current_c > trend_line) else "-"

        # MACD Sütun Yakalama
        m_h = [c for c in df.columns if 'MACD_12_26_9' in c][0]
        m_s = [c for c in df.columns if 'MACDs_12_26_9' in c][0]
        sinyal = "🚀 AL" if df[m_h].iloc[-1] > df[m_s].iloc[-1] else "BEKLE"

        return {
            "Hisse": ticker.replace(".IS", ""),
            "Fiyat": round(current_c, 2),
            "Trend Kırılım": kirilim,
            "Hedef (Fib R2)": round(r2, 2),
            "Destek (Fib S2)": round(s2, 2),
            "Sinyal": sinyal,
            "RSI": round(float(df['RSI'].iloc[-1]), 2),
            "Potansiyel %": round(((r2 / current_c) - 1) * 100, 2)
        }
    except: return None

# --- 3. ARAYÜZ (SIDEBAR) ---
st.sidebar.title("🦅 BIST 100 Strateji")
arama_hisse = st.sidebar.text_input("🎯 Hisse Sorgula (Örn: THYAO)", "").upper()
skala = st.sidebar.selectbox("Zaman Skalası", ["2 Saat", "4 Saat", "Günlük", "Haftalık", "Aylık"])
st.sidebar.divider()

# --- 4. ANA EKRAN MANTIĞI ---

# Tekil Arama
if arama_hisse:
    res = analiz_et(arama_hisse + ".IS", skala)
    if res:
        st.subheader(f"📊 {arama_hisse} Analiz Sonucu ({skala})")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fiyat", f"{res['Fiyat']} TL")
        c2.metric("Trend Kırılım", res['Trend Kırılım'])
        c3.metric("RSI", res['RSI'])
        c4.metric("Fibonacci Hedef", f"{res['Hedef (Fib R2)']} TL")
        st.table(pd.DataFrame([res]))
    else:
        st.error("Hisse kodu hatalı veya veri çekilemiyor.")
    st.divider()

# Toplu Tarama
if st.sidebar.button("🚀 BIST 100 TARAMAYI BAŞLAT"):
    liste = bist_listesi_getir()
    sonuclar = []
    bar = st.progress(0)
    durum = st.empty()
    
    for i, t in enumerate(liste):
        durum.text(f"Analiz ediliyor: {t}")
        r = analiz_et(t, skala)
        if r: sonuclar.append(r)
        if i % 15 == 0: time.sleep(0.1) # Engel yememek için minik duraklama
        bar.progress((i + 1) / len(liste))
    
    durum.success(f"Tarama Tamamlandı! ({skala})")
    if sonuclar:
        df_son = pd.DataFrame(sonuclar)
        # Önce Kırılımlar, sonra en iyi Potansiyel % olanlar
        st.table(df_son.sort_values(by=["Trend Kırılım", "Potansiyel %"], ascending=[False, False]))
