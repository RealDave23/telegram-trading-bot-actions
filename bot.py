import os
import time
import requests
import ccxt
import pandas as pd

from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange

# ================== ENV ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

# ================== CONFIG ==================
CRYPTO_PAIRS = ["BTC/USDT", "ETH/USDT"]

RSI_PERIOD = 14
RSI_BUY = 30
RSI_SELL = 70

# ================== INIT ==================
exchange = ccxt.bybit()
last_signal = {}

# ================== TELEGRAM ==================
def send_telegram(msg):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg
    })

# ================== ATR ==================
def calculate_atr(ohlcv):
    df = pd.DataFrame(
        ohlcv,
        columns=["time", "open", "high", "low", "close", "volume"]
    )
    atr = AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=14
    ).average_true_range().iloc[-1]
    return atr

# ================== DATA ==================
def get_crypto_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1m", limit=250)
    closes = [c[4] for c in ohlcv]
    volumes = [c[5] for c in ohlcv]
    atr = calculate_atr(ohlcv)
    return closes, volumes, atr

# ================== STRATEGY ==================
def process_asset(name, prices, volumes, atr):
    if len(prices) < 200:
        return

    series = pd.Series(prices)

    rsi = RSIIndicator(series, RSI_PERIOD).rsi().iloc[-1]
    ema_fast = EMAIndicator(series, window=50).ema_indicator().iloc[-1]
    ema_slow = EMAIndicator(series, window=200).ema_indicator().iloc[-1]

    price = prices[-1]

    vol_ma = pd.Series(volumes).rolling(20).mean().iloc[-1]
    volume_ok = volumes[-1] > vol_ma

    # ===== BUY =====
    if rsi < RSI_BUY and ema_fast > ema_slow and volume_ok:
        tp = price + atr * 2
        sl = price - atr

        send_telegram(
            f"🟢🟢🟢 SEGNALE DI ACQUISTO\n\n"
            f"📈 COMPRA\n"
            f"Asset: {name}\n"
            f"Prezzo: {round(price,5)}\n\n"
            f"📊 RSI: {round(rsi,2)}\n"
            f"📈 Trend rialzista\n"
            f"📊 Volume sopra la media\n\n"
            f"🎯 TP: {round(tp,5)}\n"
            f"🛑 SL: {round(sl,5)}"
        )

    # ===== SELL =====
    elif rsi > RSI_SELL and ema_fast < ema_slow and volume_ok:
        tp = price - atr * 2
        sl = price + atr

        send_telegram(
            f"🔴🔴🔴 SEGNALE DI VENDITA\n\n"
            f"📉 VENDI\n"
            f"Asset: {name}\n"
            f"Prezzo: {round(price,5)}\n\n"
            f"📊 RSI: {round(rsi,2)}\n"
            f"📉 Trend ribassista\n"
            f"📊 Volume sopra la media\n\n"
            f"🎯 TP: {round(tp,5)}\n"
            f"🛑 SL: {round(sl,5)}"
        )

# ================== RUN ONCE ==================
send_telegram("🤖 Bot attivo (GitHub Actions)")

for pair in CRYPTO_PAIRS:
    prices, volumes, atr = get_crypto_data(pair)
    process_asset(pair, prices, volumes, atr)
