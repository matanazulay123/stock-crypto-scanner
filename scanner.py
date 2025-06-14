
import requests
import pandas as pd
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from pycoingecko import CoinGeckoAPI
from dotenv import load_dotenv
import os
load_dotenv()

###################################################
# CONFIG – עדכן לפני הרצה
###################################################
recipient_email = os.getenv("RECIPIENT_EMAIL")
sender_email    = os.getenv("SENDER_EMAIL")
sender_password = os.getenv("SENDER_PASSWORD")
ma_days = 150

###################################################
# 1) פונקציות למניות
###################################################
def get_sp500_tickers_from_wikipedia():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = pd.read_html(url)[0]
    return df['Symbol'].tolist()

def check_stock_ma_slope(ticker, moving_average_days=150):
    df = yf.download(ticker, period=f"{moving_average_days + 30}d", interval="1d",
                     progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    if df.empty or len(df) < moving_average_days + 15:
        return None, None, None, None
    df['MA_150'] = df['Close'].rolling(window=moving_average_days).mean()
    if pd.isna(df['MA_150'].iloc[-1]):
        return None, None, None, None
    last_close = df['Close'].iloc[-1]
    last_ma    = df['MA_150'].iloc[-1]
    distance   = ((last_ma - last_close)/last_ma)*100
    ma_7_ago   = df['MA_150'].iloc[-8]
    ma_14_ago  = df['MA_150'].iloc[-15]
    slope_1    = ma_7_ago - ma_14_ago
    slope_2    = last_ma - ma_7_ago
    slope_status = None
    if slope_2 > 0:
        slope_status = "UPWARD"
        if slope_1 < 0:
            slope_status = "BEARISH->BULLISH"
    return distance, last_close, last_ma, slope_status

###################################################
# 2) פונקציות לקריפטו
###################################################
def get_coins_above_1B_from_coingecko():
    cg = CoinGeckoAPI()
    rows = cg.get_coins_markets(vs_currency='usd', order='market_cap_desc',
                                per_page=300, page=1)
    return [coin for coin in rows if coin['market_cap'] and coin['market_cap'] > 1_000_000_000]

def get_binance_usdt_symbols():
    data = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
    return {s['symbol'] for s in data['symbols'] if s['quoteAsset'] == 'USDT'}

def get_binance_klines(symbol, limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit={limit}"
    raw = requests.get(url).json()
    if not isinstance(raw, list):
        return pd.DataFrame()
    cols = ["open_time","open","high","low","close","volume",
            "close_time","qav","trades","tbv","tqv","ignore"]
    df = pd.DataFrame(raw, columns=cols)
    num_cols = ["open","high","low","close","volume","qav","tbv","tqv"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce')
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df.set_index('open_time', inplace=True)
    return df

def check_crypto_ma_slope(symbol_binance, days=150):
    df = get_binance_klines(symbol_binance, limit=days+30)
    if df.empty or len(df) < days+15:
        return None, None, None, None
    df['MA_150'] = df['close'].rolling(days).mean()
    if pd.isna(df['MA_150'].iloc[-1]):
        return None, None, None, None
    last_close = df['close'].iloc[-1]
    last_ma    = df['MA_150'].iloc[-1]
    distance   = ((last_ma - last_close)/last_ma)*100
    ma_7_ago   = df['MA_150'].iloc[-8]
    ma_14_ago  = df['MA_150'].iloc[-15]
    slope_1    = ma_7_ago - ma_14_ago
    slope_2    = last_ma - ma_7_ago
    slope_status = None
    if slope_2 > 0:
        slope_status = "UPWARD"
        if slope_1 < 0:
            slope_status = "BEARISH->BULLISH"
    return distance, last_close, last_ma, slope_status

###################################################
# 3) שליחת אימייל
###################################################
def send_email(subject, html_message, recipient_email, sender_email, sender_password):
    msg = MIMEText(html_message, 'html')
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(msg)
    print("Email sent!")

###################################################
# MAIN
###################################################
stocks_below, stocks_above = [], []
crypto_below, crypto_above = [], []

# A) Stocks
for tk in get_sp500_tickers_from_wikipedia():
    try:
        dist, lc, ma_val, slope = check_stock_ma_slope(tk, ma_days)
        if dist is None: continue
        if 0 <= dist <= 1:
            stocks_below.append((tk, lc, ma_val, dist, slope))
        elif -1.5 <= dist < 0:
            stocks_above.append((tk, lc, ma_val, dist, slope))
    except Exception as e:
        print("Error stock", tk, e)
stocks_below.sort(key=lambda x: x[3])
stocks_above.sort(key=lambda x: abs(x[3]))

# B) Crypto
bin_syms = get_binance_usdt_symbols()
for coin in get_coins_above_1B_from_coingecko():
    sym_bin = coin['symbol'].upper() + "USDT"
    if sym_bin not in bin_syms:
        continue
    try:
        dist, lc, ma_val, slope = check_crypto_ma_slope(sym_bin, ma_days)
        if dist is None: continue
        if 0 <= dist <= 1:
            crypto_below.append((sym_bin, lc, ma_val, dist, slope))
        elif -1.5 <= dist < 0:
            crypto_above.append((sym_bin, lc, ma_val, dist, slope))
    except Exception as e:
        print("Error crypto", sym_bin, e)
crypto_below.sort(key=lambda x: x[3])
crypto_above.sort(key=lambda x: abs(x[3]))

# C) HTML
def table_html(rows, head, bg):
    if not rows: return ""
    html = f"<h3 style='padding:10px;background:#cce5ff;border-radius:5px'>{head}</h3>"
    html += f"<table style='border-collapse:collapse;margin-bottom:20px;width:85%;background:{bg}'>"
    html += "<thead><tr style='background:#f2f2f2'><th>Symbol</th><th>Close</th><th>MA</th><th>Dist%</th><th>Slope</th></tr></thead><tbody>"
    for sym, close, ma, dist, slope in rows:
        html += f"<tr><td>{sym}</td><td>{close:.2f}</td><td>{ma:.2f}</td><td>{dist:.2f}%</td><td>{slope}</td></tr>"
    return html + "</tbody></table>"

html_body = "<html><body style='font-family:Arial'>"
html_body += table_html(stocks_below, f"Stocks below MA{ma_days} ≤1%", '#d1e7dd')
html_body += table_html(stocks_above, f"Stocks above MA{ma_days} ≤1.5%", '#cff4fc')
html_body += table_html(crypto_below, f"Crypto below MA{ma_days} ≤1%", '#d1e7dd')
html_body += table_html(crypto_above, f"Crypto above MA{ma_days} ≤1.5%", '#cff4fc')
html_body += "</body></html>"

from IPython.display import HTML, display
display(HTML(html_body))

if any([stocks_below, stocks_above, crypto_below, crypto_above]):
    send_email(f"Stocks & Crypto MA{ma_days} Scanner", html_body,
               recipient_email, sender_email, sender_password)
else:
    print("No assets matched criteria.")
