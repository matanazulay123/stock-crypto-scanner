
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
recipient_email = "matanazulay123@gmail.com"
sender_email    = "matanazulay123@gmail.com"
sender_password = "qxonvrvfzhaxjicz"  # Gmail App Password
ma_days = 150

###################################################
# 1) פונקציות למניות
###################################################
def get_sp500_tickers_from_wikipedia():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    df = pd.read_html(url)[0]
    # Some symbols from Wikipedia might have a '.' which yfinance doesn't like, e.g., 'BRK.B'.
    # yfinance prefers a '-' instead, e.g., 'BRK-B'.
    return [ticker.replace('.', '-') for ticker in df['Symbol'].tolist()]

def check_stock_ma_slope(ticker, moving_average_days=150):
    df = yf.download(ticker, period=f"{moving_average_days + 30}d", interval="1d",
                     progress=False, threads=False)
    # yfinance sometimes returns a multi-index column header, this flattens it.
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
    return [coin for coin in rows if coin.get('market_cap') and coin['market_cap'] > 1_000_000_000]

# --- MODIFIED AND FIXED FUNCTION ---
def get_binance_usdt_symbols():
    """
    Fetches all USDT trading pairs from Binance with error handling.
    """
    url = "https://api.binance.com/api/v3/exchangeInfo"
    try:
        response = requests.get(url, timeout=10)
        # Check if the request was successful (HTTP 200 OK)
        if response.status_code == 200:
            data = response.json()
            # Check if the 'symbols' key exists in the response data
            if 'symbols' in data:
                return {s['symbol'] for s in data['symbols'] if s.get('quoteAsset') == 'USDT'}
            else:
                print(f"Error: 'symbols' key not found in Binance response. Data received: {data}")
                return set() # Return an empty set to prevent script crash
        else:
            # The request failed with a non-200 status code
            print(f"Error fetching data from Binance API. Status Code: {response.status_code}, Response: {response.text}")
            return set() # Return an empty set
    except requests.exceptions.RequestException as e:
        # Handle potential network errors (e.g., timeout, connection error)
        print(f"A network error occurred while contacting Binance API: {e}")
        return set()

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
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


###################################################
# MAIN
###################################################
print("Starting scanner...")
stocks_below, stocks_above = [], []
crypto_below, crypto_above = [], []

# A) Stocks
print("Scanning S&P 500 stocks...")
sp500_tickers = get_sp500_tickers_from_wikipedia()
for i, tk in enumerate(sp500_tickers):
    print(f"  Processing stock {i+1}/{len(sp500_tickers)}: {tk}", end='\r')
    try:
        dist, lc, ma_val, slope = check_stock_ma_slope(tk, ma_days)
        if dist is None: continue
        if 0 <= dist <= 1:
            stocks_below.append((tk, lc, ma_val, dist, slope))
        elif -1.5 <= dist < 0:
            stocks_above.append((tk, lc, ma_val, dist, slope))
    except Exception as e:
        print(f"\nError processing stock {tk}: {e}")
stocks_below.sort(key=lambda x: x[3])
stocks_above.sort(key=lambda x: abs(x[3]))
print("\nStock scan complete.")

# B) Crypto
print("Scanning cryptocurrencies...")
bin_syms = get_binance_usdt_symbols()
if not bin_syms:
    print("Could not retrieve Binance symbols. Skipping crypto scan.")
else:
    coins_to_check = get_coins_above_1B_from_coingecko()
    for i, coin in enumerate(coins_to_check):
        sym_bin = coin['symbol'].upper() + "USDT"
        print(f"  Processing crypto {i+1}/{len(coins_to_check)}: {sym_bin}", end='\r')
        if sym_bin not in bin_syms:
            continue
        try:
            # Add a small delay to avoid hitting API rate limits
            time.sleep(0.2)
            dist, lc, ma_val, slope = check_crypto_ma_slope(sym_bin, ma_days)
            if dist is None: continue
            if 0 <= dist <= 1:
                crypto_below.append((sym_bin, lc, ma_val, dist, slope))
            elif -1.5 <= dist < 0:
                crypto_above.append((sym_bin, lc, ma_val, dist, slope))
        except Exception as e:
            print(f"\nError processing crypto {sym_bin}: {e}")
crypto_below.sort(key=lambda x: x[3])
crypto_above.sort(key=lambda x: abs(x[3]))
print("\nCrypto scan complete.")


# C) HTML and Email
def table_html(rows, head, bg):
    if not rows: return ""
    html = f"<h3 style='padding:10px;background:#cce5ff;border-radius:5px'>{head}</h3>"
    html += "<table style='border-collapse:collapse;margin-bottom:20px;width:85%;border:1px solid #ddd;'>"
    html += "<thead><tr style='background:#f2f2f2'><th style='padding:8px;border:1px solid #ddd;'>Symbol</th><th style='padding:8px;border:1px solid #ddd;'>Close</th><th style='padding:8px;border:1px solid #ddd;'>MA</th><th style='padding:8px;border:1px solid #ddd;'>Dist%</th><th style='padding:8px;border:1px solid #ddd;'>Slope</th></tr></thead><tbody>"
    for sym, close, ma, dist, slope in rows:
        slope_text = slope if slope is not None else "FLAT/DOWN"
        html += f"<tr style='background:{bg};'><td style='padding:8px;border:1px solid #ddd;'>{sym}</td><td style='padding:8px;border:1px solid #ddd;'>{close:.2f}</td><td style='padding:8px;border:1px solid #ddd;'>{ma:.2f}</td><td style='padding:8px;border:1px solid #ddd;'>{dist:.2f}%</td><td style='padding:8px;border:1px solid #ddd;'>{slope_text}</td></tr>"
    return html + "</tbody></table>"

html_body = "<!DOCTYPE html><html><head><style>body{font-family:Arial,sans-serif;}</style></head><body>"
html_body += table_html(stocks_below, f"Stocks below MA{ma_days} (within 1%)", '#d1e7dd')
html_body += table_html(stocks_above, f"Stocks above MA{ma_days} (within 1.5%)", '#cff4fc')
html_body += table_html(crypto_below, f"Crypto below MA{ma_days} (within 1%)", '#d1e7dd')
html_body += table_html(crypto_above, f"Crypto above MA{ma_days} (within 1.5%)", '#cff4fc')
html_body += "</body></html>"


print("\n--- Scan Results ---")
display(HTML(html_body))

if any([stocks_below, stocks_above, crypto_below, crypto_above]):
    print("\nAssets matching criteria found. Sending email...")
    send_email(f"Stocks & Crypto MA{ma_days} Scanner", html_body,
               recipient_email, sender_email, sender_password)
else:
    print("\nNo assets matched the criteria. No email sent.")
