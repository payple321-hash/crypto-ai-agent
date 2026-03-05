import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time
import os
from dotenv import load_dotenv

load_dotenv()
CRYPTOPANIC_KEY = os.getenv("CRYPTOPANIC_KEY", "")
GROQ_KEY        = os.getenv("GROQ_KEY", "")

# ─── PAGE CONFIG ───────────────────────────────────────────────
st.set_page_config(page_title="Crypto Research Agent", page_icon="🤖", layout="wide")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #07071a; }
    [data-testid="stSidebar"] { background-color: #0e0e1f; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .metric-card {
        background: #12122a; border-radius: 14px;
        padding: 18px 20px; border: 1px solid #1e1e3a; text-align: center;
    }
    .news-card {
        background: #0e0e1f; border-radius: 10px;
        padding: 12px 16px; border: 1px solid #1e1e3a;
        margin-bottom: 8px;
    }
    .section-title {
        font-size: 11px; letter-spacing: 3px; color: #4a5568;
        font-family: monospace; text-transform: uppercase; margin-bottom: 12px;
    }
    div[data-testid="metric-container"] {
        background: #12122a; border: 1px solid #1e1e3a;
        border-radius: 12px; padding: 12px 16px;
    }
</style>
""", unsafe_allow_html=True)

# ─── COIN LIST ─────────────────────────────────────────────────
ALL_COINS = {
    "Bitcoin (BTC)":    ("bitcoin",     "BTCUSDT",  "BTC"),
    "Ethereum (ETH)":   ("ethereum",    "ETHUSDT",  "ETH"),
    "Solana (SOL)":     ("solana",      "SOLUSDT",  "SOL"),
    "BNB":              ("binancecoin", "BNBUSDT",  "BNB"),
    "XRP":              ("ripple",      "XRPUSDT",  "XRP"),
    "Cardano (ADA)":    ("cardano",     "ADAUSDT",  "ADA"),
    "Avalanche (AVAX)": ("avalanche-2", "AVAXUSDT", "AVAX"),
    "Polkadot (DOT)":   ("polkadot",    "DOTUSDT",  "DOT"),
    "Chainlink (LINK)": ("chainlink",   "LINKUSDT", "LINK"),
    "Dogecoin (DOGE)":  ("dogecoin",    "DOGEUSDT", "DOGE"),
    "Litecoin (LTC)":   ("litecoin",    "LTCUSDT",  "LTC"),
    "Uniswap (UNI)":    ("uniswap",     "UNIUSDT",  "UNI"),
    "Stellar (XLM)":    ("stellar",     "XLMUSDT",  "XLM"),
}

DAYS_TO_INTERVAL = {7: "1h", 14: "2h", 30: "4h", 90: "8h"}

# ─── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown("---")
    selected_names = st.multiselect(
        "📌 Coins select karo",
        options=list(ALL_COINS.keys()),
        default=["Bitcoin (BTC)", "Ethereum (ETH)", "Solana (SOL)", "BNB"]
    )
    st.markdown("---")
    st.markdown("**📊 RSI Settings**")
    rsi_buy  = st.slider("Buy zone (RSI <)", 20, 50, 35)
    rsi_sell = st.slider("Sell zone (RSI >)", 55, 85, 65)
    st.markdown("---")
    st.markdown("**📅 Chart Period**")
    days = st.selectbox("Price history", [7, 14, 30, 90], index=0,
                        format_func=lambda x: f"{x} din")
    st.markdown("---")
    st.button("🔍 Analyse Karo!", use_container_width=True, type="primary")

# ─── HEADER ────────────────────────────────────────────────────
st.markdown("# 🤖 Crypto Research Agent")
st.markdown("*Binance TA • CoinGecko Prices • CryptoPanic News • Best coin finder*")
st.markdown("---")

if not selected_names:
    st.warning("👈 Sidebar mein kam se kam ek coin select karo!")
    st.stop()

# ─── DATA FUNCTIONS ────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_market_data(coin_list):
    """Binance se prices fetch karo — no rate limit!"""
    results = []
    for name, (gecko_id, symbol, ticker) in coin_list.items():
        try:
            # Current price from Binance ticker
            r = requests.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": symbol}, timeout=8
            )
            if r.status_code != 200:
                continue
            d = r.json()
            results.append({
                "id":           gecko_id,
                "name":         name.split(" (")[0],
                "symbol":       ticker.lower(),
                "current_price":        float(d["lastPrice"]),
                "price_change_percentage_24h":  float(d["priceChangePercent"]),
                "price_change_percentage_7d_in_currency": 0,
                "market_cap":   0,
                "total_volume": float(d["quoteVolume"]),
            })
            time.sleep(0.1)
        except:
            continue
    return results

@st.cache_data(ttl=180)
def get_binance_klines(symbol, interval="1h", limit=168):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code == 200:
            data = r.json()
            return (
                [float(d[1]) for d in data],
                [float(d[2]) for d in data],
                [float(d[3]) for d in data],
                [float(d[4]) for d in data],
                [float(d[5]) for d in data],
                [int(d[0])   for d in data],
            )
        return [], [], [], [], [], []
    except:
        return [], [], [], [], [], []

@st.cache_data(ttl=600)
def get_fear_greed():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
        d = r.json()["data"][0]
        return {"value": int(d["value"]), "label": d["value_classification"]}
    except:
        return {"value": 50, "label": "Neutral"}

@st.cache_data(ttl=600)
def get_trending():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/search/trending", timeout=8)
        return [c["item"]["name"] for c in r.json().get("coins", [])[:7]]
    except:
        return []

@st.cache_data(ttl=300)
@st.cache_data(ttl=300)
def get_news(ticker):
    """CoinGecko News API — free, no key needed!"""
    try:
        all_news = []
        # Fetch 2 pages for more coverage
        for page in range(1, 3):
            url = f"https://api.coingecko.com/api/v3/news?page={page}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                items = r.json().get("data", [])
                all_news.extend(items)
            time.sleep(0.3)

        # Filter by coin ticker/name
        keyword = ticker.lower()
        coin_names = {
            "BTC": ["bitcoin", "btc"],
            "ETH": ["ethereum", "eth"],
            "SOL": ["solana", "sol"],
            "BNB": ["bnb", "binance"],
            "XRP": ["xrp", "ripple"],
            "ADA": ["cardano", "ada"],
            "AVAX": ["avalanche", "avax"],
            "DOT": ["polkadot", "dot"],
            "LINK": ["chainlink", "link"],
            "DOGE": ["dogecoin", "doge"],
            "LTC": ["litecoin", "ltc"],
            "UNI": ["uniswap", "uni"],
            "XLM": ["stellar", "xlm"],
        }
        keywords = coin_names.get(ticker.upper(), [keyword])

        filtered = []
        for item in all_news:
            title = (item.get("title") or "").lower()
            desc  = (item.get("description") or "").lower()
            if any(kw in title or kw in desc for kw in keywords):
                filtered.append(item)

        # If no coin-specific news, return general crypto news
        return filtered[:8] if filtered else all_news[:5]
    except:
        return []

def analyze_sentiment(news_items):
    """News se sentiment calculate karo"""
    if not news_items:
        return {"score": 0, "label": "NO DATA", "color": "#4a5568", "total": 0,
                "positive": 0, "negative": 0, "neutral": 0}

    pos = neg = neu = 0
    bullish_words = ["surge","rally","bull","gain","rise","pump","high","ath",
                     "adoption","partnership","launch","upgrade","milestone",
                     "breaks","soars","buy","positive","growth","record"]
    bearish_words = ["crash","drop","bear","fall","dump","low","hack","ban",
                     "sell","fear","risk","warning","decline","plunge",
                     "lawsuit","sec","investigation","fraud","negative"]
    for item in news_items:
        title = (item.get("title") or "").lower()
        desc  = (item.get("description") or "").lower()
        text  = title + " " + desc
        if any(w in text for w in bullish_words):
            pos += 1
        elif any(w in text for w in bearish_words):
            neg += 1
        else:
            neu += 1

    total = pos + neg + neu
    if total == 0:
        score = 0
    else:
        score = round((pos - neg) / total, 2)

    if score > 0.3:
        label = "BULLISH 🟢"
        color = "#00ff88"
    elif score < -0.3:
        label = "BEARISH 🔴"
        color = "#f87171"
    else:
        label = "NEUTRAL ⚪"
        color = "#fbbf24"

    return {"score": score, "label": label, "color": color,
            "positive": pos, "negative": neg, "neutral": neu, "total": total}

# ─── TA FUNCTIONS ──────────────────────────────────────────────

def calc_rsi(closes, period=14):
    if len(closes) < period + 1: return 50.0
    d  = [closes[i]-closes[i-1] for i in range(1, len(closes))]
    ag = sum(x for x in d[-period:] if x > 0) / period
    al = sum(-x for x in d[-period:] if x < 0) / period
    return round(100.0 if al == 0 else 100-(100/(1+ag/al)), 1)

def calc_rsi_series(closes, period=14):
    out = [None]*len(closes)
    for i in range(period, len(closes)):
        seg = closes[i-period:i+1]
        d   = [seg[j]-seg[j-1] for j in range(1, len(seg))]
        ag  = sum(x for x in d if x > 0)/period
        al  = sum(-x for x in d if x < 0)/period
        out[i] = round(100.0 if al==0 else 100-(100/(1+ag/al)), 1)
    return out

def calc_ema(prices, period):
    if len(prices) < period: return prices[-1] if prices else 0
    k = 2/(period+1); e = sum(prices[:period])/period
    for p in prices[period:]: e = p*k + e*(1-k)
    return round(e, 6)

def calc_ema_series(prices, period):
    out = [None]*len(prices)
    if len(prices) < period: return out
    k = 2/(period+1); e = sum(prices[:period])/period
    out[period-1] = e
    for i in range(period, len(prices)):
        e = prices[i]*k + e*(1-k); out[i] = round(e, 6)
    return out

def calc_macd(prices):
    if len(prices) < 26: return 0, 0
    return round(calc_ema(prices,12)-calc_ema(prices,26), 4), \
           round(calc_ema([calc_ema(prices,12)-calc_ema(prices,26)]*9, 9), 4)

def calc_macd_series(prices):
    om = [None]*len(prices); os = [None]*len(prices)
    if len(prices) < 35: return om, os
    e12 = calc_ema_series(prices, 12); e26 = calc_ema_series(prices, 26)
    mv = []; mi = []
    for i in range(len(prices)):
        if e12[i] and e26[i]:
            mv.append(e12[i]-e26[i]); mi.append(i); om[i] = round(mv[-1],4)
    if len(mv) >= 9:
        ss = calc_ema_series(mv, 9)
        for j,idx in enumerate(mi):
            if ss[j]: os[idx] = round(ss[j], 4)
    return om, os

def get_signal(rsi, macd, msig, price, ema20, ema50, chg24, sentiment_score):
    score = 0; reasons = []

    if rsi < rsi_buy:
        score += 2; reasons.append(("✅", f"RSI {rsi} — Oversold, buy zone"))
    elif rsi > rsi_sell:
        score -= 2; reasons.append(("❌", f"RSI {rsi} — Overbought, sell zone"))
    else:
        reasons.append(("⚪", f"RSI {rsi} — Neutral"))

    if macd > msig:
        score += 1; reasons.append(("✅", "MACD bullish momentum"))
    else:
        score -= 1; reasons.append(("❌", "MACD bearish momentum"))

    if price > ema20:
        score += 1; reasons.append(("✅", "Price EMA20 ke upar — Uptrend"))
    else:
        score -= 1; reasons.append(("❌", "Price EMA20 ke neeche — Downtrend"))

    if ema20 > ema50 and ema50 > 0:
        score += 1; reasons.append(("✅", "EMA20 > EMA50 — Golden cross"))
    elif ema50 > 0:
        score -= 1; reasons.append(("❌", "EMA20 < EMA50 — Death cross"))

    if chg24 > 3:
        score += 1; reasons.append(("✅", f"24h +{chg24:.1f}% — Strong buying"))
    elif chg24 < -3:
        score -= 1; reasons.append(("❌", f"24h {chg24:.1f}% — Strong selling"))
    else:
        reasons.append(("⚪", f"24h {chg24:.1f}% — Stable"))

    # News sentiment bonus
    if sentiment_score > 0.3:
        score += 1; reasons.append(("✅", f"News bullish (score: {sentiment_score:+.2f})"))
    elif sentiment_score < -0.3:
        score -= 1; reasons.append(("❌", f"News bearish (score: {sentiment_score:+.2f})"))
    else:
        reasons.append(("⚪", f"News neutral (score: {sentiment_score:+.2f})"))

    if score >= 4:    return "🟢 STRONG BUY",  "buy",  score, reasons
    elif score >= 2:  return "🟡 BUY",          "buy",  score, reasons
    elif score <= -4: return "🔴 STRONG SELL",  "sell", score, reasons
    elif score <= -2: return "🔴 SELL",         "sell", score, reasons
    else:             return "⚪ HOLD",          "hold", score, reasons

# ─── FETCH BASE DATA ───────────────────────────────────────────
interval  = DAYS_TO_INTERVAL.get(days, "1h")
selected_coins_dict = {n: ALL_COINS[n] for n in selected_names}

with st.spinner("📡 Data fetch ho raha hai..."):
    market_data = get_market_data(selected_coins_dict)
    fear_greed  = get_fear_greed()
    trending    = get_trending()

if not market_data:
    st.error("❌ CoinGecko data nahi aaya."); st.stop()

market_map = {c["id"]: c for c in market_data}

# ─── MARKET OVERVIEW ───────────────────────────────────────────
st.markdown('<div class="section-title">// Market Overview</div>', unsafe_allow_html=True)

fg_val   = fear_greed["value"]
fg_color = "#00ff88" if fg_val > 60 else "#f87171" if fg_val < 40 else "#fbbf24"

top_cols = st.columns([1] + [1]*min(len(market_data), 4))
with top_cols[0]:
    st.markdown(f"""
    <div class="metric-card" style="border-color:{fg_color}44">
        <div style="font-size:11px;color:#4a5568;font-family:monospace;letter-spacing:2px">FEAR & GREED</div>
        <div style="font-size:36px;font-weight:800;color:{fg_color}">{fg_val}</div>
        <div style="font-size:13px;color:{fg_color}">{fear_greed['label']}</div>
    </div>
    """, unsafe_allow_html=True)

for i, coin in enumerate(market_data[:4]):
    chg = coin.get("price_change_percentage_24h") or 0
    c = "#00ff88" if chg >= 0 else "#f87171"
    with top_cols[i+1]:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size:11px;color:#4a5568;font-family:monospace">{coin['symbol'].upper()}</div>
            <div style="font-size:20px;font-weight:800;color:#e2e8f0">${coin['current_price']:,.2f}</div>
            <div style="font-size:13px;color:{c};font-weight:700">{chg:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ─── ANALYSE ALL COINS ─────────────────────────────────────────
results  = []
progress = st.progress(0, text="Coins analyse ho rahe hain...")

for idx, name in enumerate(selected_names):
    gecko_id = ALL_COINS[name][0]
    symbol   = ALL_COINS[name][1]
    ticker   = ALL_COINS[name][2]
    coin     = market_map.get(gecko_id, {})

    price   = coin.get("current_price", 0)
    chg_24h = coin.get("price_change_percentage_24h") or 0
    chg_7d  = coin.get("price_change_percentage_7d_in_currency") or 0

    opens, highs, lows, closes, vols, times = get_binance_klines(symbol, interval)

    if len(closes) > 26:
        rsi          = calc_rsi(closes)
        rsi_series   = calc_rsi_series(closes)
        ema20        = calc_ema(closes, 20)
        ema50        = calc_ema(closes, 50) if len(closes)>=50 else calc_ema(closes, len(closes)//2)
        ema20_series = calc_ema_series(closes, 20)
        ema50_series = calc_ema_series(closes, 50)
        macd_val, macd_sig = calc_macd(closes)
        macd_series, msig_series = calc_macd_series(closes)
    else:
        rsi=50; rsi_series=[]; ema20=price; ema50=price
        ema20_series=[]; ema50_series=[]; macd_val=macd_sig=0
        macd_series=[]; msig_series=[]

    # News fetch
    news_items = get_news(ticker)
    sentiment  = analyze_sentiment(news_items)

    signal, sig_type, score, reasons = get_signal(
        rsi, macd_val, macd_sig, price, ema20, ema50, chg_24h, sentiment["score"]
    )

    results.append({
        "name": name, "coin": coin.get("name", name),
        "sym": coin.get("symbol","").upper(), "ticker": ticker,
        "price": price, "chg_24h": chg_24h, "chg_7d": chg_7d,
        "rsi": rsi, "rsi_series": rsi_series,
        "ema20": round(ema20,2), "ema50": round(ema50,2),
        "ema20_series": ema20_series, "ema50_series": ema50_series,
        "macd": macd_val, "macd_sig": macd_sig,
        "macd_series": macd_series, "msig_series": msig_series,
        "signal": signal, "sig_type": sig_type, "score": score,
        "reasons": reasons, "sentiment": sentiment,
        "news_items": news_items,
        "trending": coin.get("name", name) in trending,
        "mktcap": coin.get("market_cap") or 0,
        "volume": coin.get("total_volume") or 0,
        "opens": opens, "highs": highs, "lows": lows,
        "closes": closes, "vols": vols, "times": times
    })

    progress.progress((idx+1)/len(selected_names),
                      text=f"✅ {name} — RSI: {rsi} | News: {sentiment['label']}")
    time.sleep(0.3)

progress.empty()
results.sort(key=lambda x: x["score"], reverse=True)

# ─── BEST PICK ─────────────────────────────────────────────────
best = results[0]
bc   = "#00ff88" if best["sig_type"]=="buy" else "#f87171" if best["sig_type"]=="sell" else "#fbbf24"

st.markdown('<div class="section-title">// Best Coin Right Now</div>', unsafe_allow_html=True)
st.markdown(f"""
<div style="background:linear-gradient(135deg,#0a1a10,#07071a);border:1px solid {bc}44;
            border-radius:18px;padding:24px 28px;margin-bottom:24px">
    <div style="font-size:10px;color:{bc};letter-spacing:4px;font-family:monospace">// AI RECOMMENDATION</div>
    <div style="font-size:32px;font-weight:800;color:#fff;margin:10px 0 4px">
        {best['coin']} <span style="color:#4a5568;font-size:20px">({best['sym']})</span>
    </div>
    <div style="font-size:24px;font-weight:800;color:{bc}">{best['signal']}</div>
    <div style="margin-top:12px;display:flex;gap:20px;flex-wrap:wrap">
        <span style="font-size:13px;color:#64748b;font-family:monospace">
            Score: {best['score']}/6 &nbsp;·&nbsp; RSI: {best['rsi']} &nbsp;·&nbsp;
            Price: ${best['price']:,.4f} &nbsp;·&nbsp; 24h: {best['chg_24h']:+.2f}%
        </span>
        <span style="font-size:13px;font-weight:700;color:{best['sentiment']['color']}">
            📰 News: {best['sentiment']['label']}
        </span>
        {'<span style="font-size:13px;color:#fbbf24">🔥 Trending!</span>' if best['trending'] else ''}
    </div>
</div>
""", unsafe_allow_html=True)

# ─── COIN CARDS ────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">// Coin-by-Coin Analysis</div>', unsafe_allow_html=True)

for r in results:
    sc = "#00ff88" if r["sig_type"]=="buy" else "#f87171" if r["sig_type"]=="sell" else "#fbbf24"
    sent = r["sentiment"]

    with st.expander(
        f"{r['signal']}  ·  {r['coin']} ({r['sym']})  ·  "
        f"${r['price']:,.4f}  ·  Score: {r['score']}/6  ·  "
        f"News: {sent['label']}"
    ):
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("💰 Price",  f"${r['price']:,.2f}")
        m2.metric("📊 RSI",    r['rsi'],
                  delta="oversold ✅" if r['rsi']<rsi_buy else ("overbought ⚠️" if r['rsi']>rsi_sell else "neutral"))
        m3.metric("⚡ MACD",   r['macd'])
        m4.metric("📈 24h",    f"{r['chg_24h']:+.2f}%")
        m5.metric("📅 7d",     f"{r['chg_7d']:+.2f}%")

        # ── TABS: Chart | News ─────────────────────────────────
        tab_chart, tab_news = st.tabs(["📊 Technical Chart", "📰 News & Sentiment"])

        # ── CHART TAB ─────────────────────────────────────────
        with tab_chart:
            if len(r["closes"]) > 20:
                times_dt = [datetime.fromtimestamp(t/1000) for t in r["times"]]
                fig = make_subplots(
                    rows=3, cols=1, shared_xaxes=True,
                    row_heights=[0.50, 0.25, 0.25],
                    vertical_spacing=0.04,
                    subplot_titles=["📈 Price + EMA", "📊 RSI", "⚡ MACD"]
                )

                fig.add_trace(go.Candlestick(
                    x=times_dt,
                    open=r["opens"], high=r["highs"],
                    low=r["lows"],   close=r["closes"],
                    name="Price",
                    increasing_line_color="#00ff88",
                    decreasing_line_color="#f87171",
                    increasing_fillcolor="rgba(0,255,136,0.3)",
                    decreasing_fillcolor="rgba(248,113,113,0.3)",
                ), row=1, col=1)

                e20 = [v for v in r["ema20_series"] if v]
                if e20:
                    fig.add_trace(go.Scatter(
                        x=times_dt[-len(e20):], y=e20, mode="lines",
                        name="EMA20", line=dict(color="#38bdf8", width=1.5)
                    ), row=1, col=1)

                e50 = [v for v in r["ema50_series"] if v]
                if e50:
                    fig.add_trace(go.Scatter(
                        x=times_dt[-len(e50):], y=e50, mode="lines",
                        name="EMA50", line=dict(color="#a78bfa", width=1.5)
                    ), row=1, col=1)

                rsi_c = [v for v in r["rsi_series"] if v]
                if rsi_c:
                    fig.add_trace(go.Scatter(
                        x=times_dt[-len(rsi_c):], y=rsi_c, mode="lines",
                        name="RSI", line=dict(color="#fbbf24", width=1.5)
                    ), row=2, col=1)
                    fig.add_hline(y=rsi_buy,  line_dash="dot", line_color="#00ff88", opacity=0.5, row=2, col=1)
                    fig.add_hline(y=rsi_sell, line_dash="dot", line_color="#f87171", opacity=0.5, row=2, col=1)
                    fig.add_hline(y=50,       line_dash="dot", line_color="#ffffff",  opacity=0.15, row=2, col=1)

                mc = [v for v in r["macd_series"] if v is not None]
                ms = [v for v in r["msig_series"] if v is not None]
                if mc and ms:
                    n = min(len(mc), len(ms))
                    fig.add_trace(go.Scatter(
                        x=times_dt[-n:], y=mc[-n:], mode="lines",
                        name="MACD", line=dict(color="#38bdf8", width=1.5)
                    ), row=3, col=1)
                    fig.add_trace(go.Scatter(
                        x=times_dt[-n:], y=ms[-n:], mode="lines",
                        name="Signal", line=dict(color="#f472b6", width=1.2, dash="dot")
                    ), row=3, col=1)
                    hist = [m-s for m,s in zip(mc[-n:], ms[-n:])]
                    fig.add_trace(go.Bar(
                        x=times_dt[-n:], y=hist, name="Hist",
                        marker_color=["rgba(0,255,136,0.4)" if h>=0 else "rgba(248,113,113,0.4)" for h in hist]
                    ), row=3, col=1)

                fig.update_layout(
                    height=560, paper_bgcolor="#07071a", plot_bgcolor="#07071a",
                    font=dict(color="#94a3b8", size=11),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=10,r=10,t=40,b=10),
                    xaxis_rangeslider_visible=False
                )
                fig.update_xaxes(gridcolor="#1e1e3a", zeroline=False)
                fig.update_yaxes(gridcolor="#1e1e3a", zeroline=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 Enough data nahi hai chart ke liye.")

        # ── NEWS TAB ──────────────────────────────────────────
        with tab_news:
            # Sentiment summary
            s = r["sentiment"]
            st.markdown(f"""
            <div style="background:#0e0e1f;border:1px solid {s['color']}44;border-radius:12px;
                        padding:16px 20px;margin-bottom:16px">
                <div style="font-size:10px;color:#4a5568;font-family:monospace;letter-spacing:3px">
                    // NEWS SENTIMENT
                </div>
                <div style="font-size:24px;font-weight:800;color:{s['color']};margin:8px 0">
                    {s['label']}
                </div>
                <div style="display:flex;gap:20px;margin-top:8px">
                    <span style="color:#00ff88;font-size:13px">✅ Positive: {s['positive']}</span>
                    <span style="color:#f87171;font-size:13px">❌ Negative: {s['negative']}</span>
                    <span style="color:#fbbf24;font-size:13px">⚪ Neutral: {s['neutral']}</span>
                    <span style="color:#64748b;font-size:13px">Total: {s['total']} news</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # News list
            if r["news_items"]:
                for news in r["news_items"]:
                    title  = news.get("title") or "No title"
                    url    = news.get("url") or "#"
                    author = news.get("author") or "Unknown"
                    desc   = news.get("description") or ""
                    ts     = news.get("created_at") or 0
                    pub    = datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "Unknown"

                    # Sentiment from title keywords
                    t = title.lower()
                    bullish = ["surge","rally","bull","gain","rise","pump","high","ath",
                               "adoption","partnership","launch","upgrade","breaks","soars","buy"]
                    bearish = ["crash","drop","bear","fall","dump","low","hack","ban",
                               "sell","fear","risk","warning","decline","plunge","lawsuit","sec"]
                    if any(w in t for w in bullish):
                        n_color = "#00ff88"; n_icon = "🟢"
                    elif any(w in t for w in bearish):
                        n_color = "#f87171"; n_icon = "🔴"
                    else:
                        n_color = "#fbbf24"; n_icon = "⚪"

                    st.markdown(f"""
                    <div class="news-card" style="border-left:3px solid {n_color}">
                        <a href="{url}" target="_blank"
                           style="color:#e2e8f0;text-decoration:none;font-size:13px;
                                  line-height:1.5;font-weight:600">
                            {n_icon} {title}
                        </a>
                        <div style="margin-top:6px;font-size:12px;color:#64748b;line-height:1.5">
                            {desc[:120]}{"..." if len(desc)>120 else ""}
                        </div>
                        <div style="margin-top:6px;font-size:11px;color:#4a5568;font-family:monospace">
                            ✍️ {author} &nbsp;·&nbsp; 📅 {pub}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📰 Is coin ki news abhi available nahi hai.")

        # Analysis reasons
        st.markdown("**🧠 Analysis Reasons:**")
        rc1, rc2 = st.columns(2)
        for i, (icon, reason) in enumerate(r["reasons"]):
            (rc1 if i%2==0 else rc2).markdown(f"{icon} {reason}")

        st.markdown(f"""
        <div style="margin-top:14px;padding:12px 16px;background:#0e0e1f;
                    border-radius:10px;font-family:monospace;font-size:12px;color:#4a5568">
            Mkt Cap: ${r['mktcap']:,.0f} &nbsp;·&nbsp; Vol 24h: ${r['volume']:,.0f}
            &nbsp;·&nbsp; EMA20: ${r['ema20']:,.2f} &nbsp;·&nbsp; EMA50: ${r['ema50']:,.2f}
            {'&nbsp;·&nbsp; 🔥 Trending!' if r['trending'] else ''}
        </div>
        """, unsafe_allow_html=True)

# ─── COMPARISON TABLE ──────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">// Full Comparison Table</div>', unsafe_allow_html=True)

df = pd.DataFrame([{
    "Coin":        r["coin"],
    "Symbol":      r["sym"],
    "Price $":     r["price"],
    "24h %":       round(r["chg_24h"], 2),
    "7d %":        round(r["chg_7d"], 2),
    "RSI":         r["rsi"],
    "MACD":        r["macd"],
    "News":        r["sentiment"]["label"],
    "Signal":      r["signal"],
    "Score /6":    r["score"],
    "Trending":    "🔥" if r["trending"] else ""
} for r in results])

st.dataframe(df, use_container_width=True, hide_index=True)

# ─── TRENDING ──────────────────────────────────────────────────
if trending:
    st.markdown("---")
    st.markdown('<div class="section-title">// CoinGecko Trending</div>', unsafe_allow_html=True)
    tcols = st.columns(len(trending[:7]))
    for i, t in enumerate(trending[:7]):
        with tcols[i]:
            st.markdown(f"""
            <div style="background:#12122a;border:1px solid #1e1e3a;border-radius:10px;
                        padding:10px;text-align:center;font-size:12px;color:#e2e8f0">🔥 {t}</div>
            """, unsafe_allow_html=True)


# ─── AI SUMMARY ────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">// AI Agent — Best Coin Recommendation</div>', unsafe_allow_html=True)

if not GROQ_KEY:
    st.warning("⚠️ GROQ_KEY .env mein nahi hai!")
else:
    if st.button("🤖 AI Se Best Coin Poochho!", use_container_width=True, type="primary"):
        with st.spinner("🧠 AI poora dashboard analyse kar raha hai..."):

            lines = ["Current crypto market analysis:\n"]
            for r in results:
                rsi_label = "oversold-bullish" if r["rsi"] < 35 else ("overbought-bearish" if r["rsi"] > 65 else "neutral")
                macd_label = "bullish" if r["macd"] > r["macd_sig"] else "bearish"
                trend_label = "uptrend" if r["price"] > r["ema20"] else "downtrend"
                lines.append("Coin: " + r["coin"] + " (" + r["sym"] + ")")
                lines.append("Price: $" + str(round(r["price"], 2)))
                lines.append("24h: " + str(round(r["chg_24h"], 2)) + "%")
                lines.append("7d: " + str(round(r["chg_7d"], 2)) + "%")
                lines.append("RSI: " + str(r["rsi"]) + " - " + rsi_label)
                lines.append("MACD: " + str(r["macd"]) + " - " + macd_label)
                lines.append("Trend: " + trend_label)
                lines.append("News: " + r["sentiment"]["label"] + " (score: " + str(r["sentiment"]["score"]) + ")")
                lines.append("Signal: " + r["signal"])
                lines.append("Score: " + str(r["score"]) + "/6")
                lines.append("---")

            lines.append("Fear & Greed: " + str(fear_greed["value"]) + " - " + fear_greed["label"])
            summary_text = "\n".join(lines)

            prompt = (
                "You are a professional crypto research analyst. "
                "Based on the following real-time market data, give a clear recommendation in Hinglish (Hindi+English mix).\n\n"
                + summary_text +
                "\n\nPlease provide:\n"
                "1. BEST COIN abhi kaunsa hai aur kyun (RSI, MACD, news, trend mention karo)\n"
                "2. AVOID karne wale coins aur kyun\n"
                "3. Overall market sentiment (bullish/bearish)\n"
                "4. Entry price suggestion\n"
                "5. Risk warning\n\n"
                "Concise rakho, emojis use karo, Hinglish mein likho."
            )

            try:
                from groq import Groq
                client = Groq(api_key=GROQ_KEY)
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                    temperature=0.7
                )
                ai_reply = response.choices[0].message.content

                st.markdown("""
                <div style="background:linear-gradient(135deg,#0a0a1f,#0d1a0d);
                            border:1px solid #00ff8844;border-radius:16px;padding:24px 28px">
                    <div style="font-size:10px;color:#00ff88;letter-spacing:4px;
                                font-family:monospace;margin-bottom:12px">
                        // AI AGENT RECOMMENDATION
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(ai_reply)
                st.caption("Powered by Groq (Llama 3.3 70B) · ⚠️ Not financial advice")

            except Exception as e:
                st.error("❌ Error: " + str(e))

# ─── FOOTER ────────────────────────────────────────────────────
st.markdown("---")
st.caption("Updated: " + datetime.now().strftime("%d %b %Y · %H:%M:%S") + " · Binance + CoinGecko + Groq AI · ⚠️ Research only")