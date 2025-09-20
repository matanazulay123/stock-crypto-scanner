import os
import smtplib
from datetime import datetime
import pandas as pd
import yfinance as yf
from email.mime.text import MIMEText
from IPython.display import HTML, display
import requests
from io import StringIO
load_dotenv()





 ###################################################
# CONFIG – עדכן לפני הרצה
###################################################
MA_DAYS           = 150
RECIPIENT_EMAIL   = "matanazul23@gmail.com"
SENDER_EMAIL      = "matanazul23@gmail.com"
SENDER_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD")


# ASSET DATA FUNCTIONS (STOCKS & CRYPTO)

def get_sp500_tickers() -> tuple[list[str], str]:
    apis = [
        ("Wikipedia", "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"),
        ("GitHubCSV", "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"),
        ("FMP", "https://financialmodelingprep.com/api/v3/sp500_constituent"),
        ("GitHubAlt", "https://raw.githubusercontent.com/fja05680/sp500/master/S%26P%20500%20Historical%20Components%20%26%20Changes(03-17-2023).csv"),
    ]
    for name, url in apis:
            if name in ["Wikipedia", "GitHubAlt"]:
                headers = {}
                if name == "Wikipedia":
                    headers = {
                        'User-Agent': 'Mozilla/5.0',
                        'Accept': 'text/html',
                    }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                if name == "Wikipedia":
                    tables = pd.read_html(StringIO(response.text))
                    df = tables[0]
                    tickers = [sym.replace('.', '-') for sym in df['Symbol'].tolist()]
                else:
                    df = pd.read_csv(StringIO(response.text))
                    last_col = df.columns[-1]
                    tickers = df[last_col].dropna().tolist()
                    tickers = [sym.replace('.', '-') for sym in tickers if pd.notna(sym)]
                tickers.append('^GSPC')
                return tickers, name
            elif name == "GitHubCSV":
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                df = pd.read_csv(StringIO(response.text))
                tickers = [sym.replace('.', '-') for sym in df['Symbol'].tolist()]
                tickers.append('^GSPC')
                return tickers, name
            elif name == "FMP":
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                tickers = [item['symbol'].replace('.', '-') for item in data]
                tickers.append('^GSPC')
                return tickers, name

def get_crypto_tickers() -> list[str]:
    raw = [
        'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'DOGE', 'ADA', 'TRX',
        'BCH', 'LINK', 'AVAX', 'XLM', 'TON', 'SHIB', 'LTC',
        'HBAR', 'XMR', 'DOT', 'AAVE',
        'NEAR', 'ICP', 'ETC', 'VET', 'ARB',
        'ATOM', 'FIL', 'ALGO', 'WLD', 'SEI', 'JUP', 'BONK', 'QNT',
        'FLR', 'INJ', 'TIA', 'STX'
    ]
    return [f"{t}-USD" for t in raw]

def process_assets_in_batch(tickers: list, asset_type: str, days: int = MA_DAYS) -> list[dict]:
    if not tickers:
        return []
    try:
        data = yf.download(
            tickers,
            period=f"{days+20}d",
            interval="1d",
            progress=False,
            threads=True,
            group_by='ticker',
            auto_adjust=True
        )
        if data.empty:
            return []
    except Exception:
        return []

    results = []
    if len(tickers) == 1:
        df = data.dropna(subset=['Close'])
        if len(df) < days:
            return []
        res = process_single_ticker(tickers[0], df, days)
        if res:
            results.append(res)
    else:
        if hasattr(data.columns, 'nlevels') and data.columns.nlevels > 1:
            tickers_in_data = data.columns.get_level_values(0).unique()
            for ticker in tickers_in_data:
                df = data[ticker].dropna(subset=['Close'])
                if len(df) < days:
                    continue
                res = process_single_ticker(ticker, df, days)
                if res:
                    results.append(res)
        else:
            df = data.dropna(subset=['Close'])
            if len(df) >= days:
                res = process_single_ticker(tickers[0], df, days)
                if res:
                    results.append(res)
    return results

def process_single_ticker(ticker: str, df: pd.DataFrame, days: int) -> dict:
    df['MA'] = df['Close'].rolling(days).mean()
    if pd.isna(df['MA'].iloc[-1]):
        return None
    last_close = df['Close'].iloc[-1]
    last_ma = df['MA'].iloc[-1]
    dist_pct = ((last_ma - last_close) / last_ma) * 100
    slope_tag = "UPWARD" if last_ma > df['MA'].iloc[-8] else "DOWNWARD" if len(df['MA'].dropna()) > 7 else "N/A"
    return {'ticker': ticker, 'price': last_close, 'ma': last_ma, 'dist_pct': dist_pct, 'slope': slope_tag}

def send_email(subject: str, html: str):
    if not SENDER_PASSWORD:
        print("No email password set, skipping email.")
        return
    msg = MIMEText(html, 'html')
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print("[INFO] Email sent!")
    except Exception as e:
        print(f"Email send failed: {e}")

BASE_STYLE = """
<style>
body{font-family:Arial,sans-serif;direction:rtl;text-align:right;background:#fafafa;margin:0;padding:0;}
table{width:96%;border-collapse:collapse;margin:20px auto;font-size:14px;box-shadow:0 2px 8px rgba(0,0,0,.05);}
thead tr{background:#1565c0;color:#fff;}
th,td{padding:12px 10px;border-left:1px solid #ddd;}
th:last-child, td:last-child {border-left:none;}
tbody tr:nth-child(even){background:#f1f5f9;}
tbody tr:hover{background:#e3f2fd;}
h3{color:#1565c0;margin:24px 24px 6px 0;font-weight:600;}
</style>
"""

def make_table(rows, title):
    if not rows: return ""
    html = f"<h3>{title}</h3><table><thead><tr><th>שיפוע</th><th>% מרחק</th><th>ממוצע נע 150</th><th>מחיר נוכחי</th><th>סימול</th></tr></thead><tbody>"
    for sym, price, ma, dist, slope in rows:
        disp_sym = sym.replace('-USD','')
        html += f"<tr><td>{slope or '—'}</td><td>{dist:.2f}%</td><td>${ma:,.2f}</td><td>${price:,.2f}</td><td>{disp_sym}</td></tr>"
    html += "</tbody></table>"
    return html

def main():
    print("🚀 Scanner started:", datetime.now().strftime("%Y-%m-%d %H:%M"))
    sp500_tickers, api = get_sp500_tickers()

    stock_results = process_assets_in_batch(sp500_tickers, "stock")
    crypto_results = process_assets_in_batch(get_crypto_tickers(), "crypto")

    def sort_cat(results):
        below, above = [], []
        for r in results:
            dist = r['dist_pct']
            row = (r['ticker'], r['price'], r['ma'], dist, r['slope'])
            if 0 <= dist <= 1.0: below.append(row)
            elif -1.5 <= dist < 0: above.append(row)
        below.sort(key=lambda x: x[3])
        above.sort(key=lambda x: abs(x[3]))
        return below, above

    stocks_below, stocks_above = sort_cat(stock_results)
    crypto_below, crypto_above = sort_cat(crypto_results)

    total = len(stocks_below) + len(stocks_above) + len(crypto_below) + len(crypto_above)
    if total > 0:
        print(f"Found {total} matching assets. Building report...")
        html = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{BASE_STYLE}</head><body>"
        html += f"<h2 style='text-align:right;margin-right:24px;'>דוח סורק ממוצע נע {MA_DAYS} - {datetime.now().strftime('%d/%m/%Y')}</h2>"
        html += f"<h4 style='color:gray;text-align:right;'>מקור מניות S&P500: <b>{api}</b></h4>"
        html += make_table(stocks_below, "מניות מתחת לממוצע (עד 1%)")
        html += make_table(stocks_above, "מניות מעל הממוצע (עד 1.5%)")
        html += make_table(crypto_below, "קריפטו מתחת לממוצע (עד 1%)")
        html += make_table(crypto_above, "קריפטו מעל הממוצע (עד 1.5%)")
        html += "</body></html>"
        display(HTML(html))
        send_email(f"Scanner Results MA{MA_DAYS} - {datetime.now().strftime('%d-%m-%Y')}", html)
    else:
        print("No matching assets found. No email sent.")

if __name__ == "__main__":
    main()

