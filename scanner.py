import os
import smtplib
from datetime import datetime
import pandas as pd
import yfinance as yf
from email.mime.text import MIMEText
from IPython.display import HTML, display
load_dotenv()


 ###################################################
# CONFIG – עדכן לפני הרצה
###################################################
MA_DAYS           = 150
RECIPIENT_EMAIL   = "matanazul23@gmail.com"
SENDER_EMAIL      = "matanazul23@gmail.com"
SENDER_PASSWORD   = os.getenv("GMAIL_APP_PASSWORD")


# ASSET DATA FUNCTIONS (STOCKS & CRYPTO)


def get_sp500_tickers() -> list[str]:
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        df  = pd.read_html(url)[0]
        tickers = [sym.replace('.', '-') for sym in df['Symbol'].tolist()]
        tickers.append('^GSPC') # הוספת מדד ה-S&P 500 עצמו (סימול SPX)
        return tickers
    except Exception as e:
        print(f"[ERROR] Failed to fetch S&P 500 tickers: {e}")
        return []

def get_crypto_tickers() -> list[str]:
    raw_tickers = [
        'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'TRX', 'DOGE', 'ADA', 'HYPE', 
        'BCH', 'SUI', 'LINK', 'LEO', 'AVAX', 'XLM', 'TON', 'SHIB', 'LTC',
        'HBAR', 'XMR', 'DOT', 'BGB', 'UNI', 'PEPE', 'AAVE', 'PI',
        'APT', 'OKB', 'TAO', 'NEAR', 'ICP', 'ETC', 'ONDO', 'KAS', 'POL', 
        'MNT', 'GT', 'VET', 'TRUMP', 'SKY', 'ARB', 'RENDER', 'FET', 'ENA',
        'ATOM', 'FIL', 'ALGO', 'WLD', 'SEI', 'KCS', 'JUP', 'BONK', 'QNT',
        'FLR', 'INJ', 'TIA', 'FOUR', 'STX'
    ]
    
    # 'SYMBOL-USD'
    return [f"{ticker.upper()}-USD" for ticker in raw_tickers]

def process_assets_in_batch(tickers: list, asset_type: str, days: int = MA_DAYS) -> list[dict]:
   
    if not tickers:
        return []
        
    print(f"\n[INFO] Downloading data for {len(tickers)} {asset_type} assets at once...")
    all_data = yf.download(
        tickers, 
        period=f"{days+50}d",
        interval="1d", 
        progress=True, 
        threads=True,
        group_by='ticker',
        auto_adjust=True
    )
    
    results = []
    
    print(f"[INFO] Processing {asset_type} data...")

    valid_tickers = all_data.columns.get_level_values(0).unique()
    for ticker in valid_tickers:
        try:
            df = all_data[ticker].copy()
            df.dropna(subset=['Close'], inplace=True)
            
            if df.empty or len(df) < days + 15:
                continue
            
            df['MA'] = df['Close'].rolling(days).mean()
            if pd.isna(df['MA'].iloc[-1]):
                continue
            
            last_close = df['Close'].iloc[-1]
            last_ma    = df['MA'].iloc[-1]
            dist_pct   = ((last_ma - last_close) / last_ma) * 100
            
            if len(df['MA'].dropna()) > 15:
                slope_7    = df['MA'].iloc[-8]  - df['MA'].iloc[-15]
                slope_now  = last_ma - df['MA'].iloc[-8]
                slope_tag  = "UPWARD" if slope_now > 0 else "DOWNWARD"
                if slope_now > 0 and slope_7 < 0:
                    slope_tag = "BEARISH→BULLISH"
            else:
                slope_tag = "N/A"

            results.append({
                'ticker': ticker,
                'price': last_close,
                'ma': last_ma,
                'dist_pct': dist_pct,
                'slope': slope_tag
            })
            
        except Exception as e:
            print(f"\n[WARN] Error processing {ticker}: {e}")
            continue
            
    print(f"[INFO] {asset_type.capitalize()} processing complete.")
    return results

# EMAIL & HTML

def send_email(subject: str, html_body: str):
    if not SENDER_PASSWORD:
        print("[WARN] Email not sent because SENDER_PASSWORD environment variable is not set.")
        return
    try:
        msg = MIMEText(html_body, 'html', 'utf-8')
        msg['Subject'] = subject; msg['From'] = SENDER_EMAIL; msg['To'] = RECIPIENT_EMAIL
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(SENDER_EMAIL, SENDER_PASSWORD)
            s.send_message(msg)
        print("[INFO] Email sent! 🎉")
    except Exception as e:
        print(f"[ERROR] Email failed: {e}")

BASE_STYLE = """
<style>
  body{font-family:Arial,Helvetica,sans-serif;margin:0;padding:0;background:#fafafa;direction:rtl;text-align:right;}
  table{border-collapse:collapse;width:96%;margin:20px auto;font-size:14px;border-radius:6px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.05)}
  thead tr{background:#1565c0;color:#fff}
  th,td{padding:12px 10px;text-align:right;border-left: 1px solid #ddd;}
  th:last-child, td:last-child {border-left: none;}
  tbody tr:nth-child(even){background:#f1f5f9}
  tbody tr:hover{background:#e3f2fd}
  h3{margin:24px 24px 6px 0;color:#1565c0;font-weight:600}
</style>
"""

def make_table(rows, title):
    if not rows: return ""
    html = f"<h3>{title}</h3>"
    html += ("<table><thead><tr>"
             "<th>שיפוע</th><th>% מרחק</th><th>ממוצע נע 150</th>"
             "<th>מחיר נוכחי</th><th>סימול</th></tr></thead><tbody>")
    for sym, price, ma, dist, slope in rows:
        slope_str = slope or "—"
        display_sym = sym.replace('-USD', '')
        html += (f"<tr><td>{slope_str}</td><td>{dist:.2f}%</td><td>${ma:,.2f}</td>"
                 f"<td>${price:,.2f}</td><td>{display_sym}</td></tr>")
    html += "</tbody></table>"
    return html

# MAIN

def main():
    print("🚀  Scanner started:", datetime.now().strftime("%Y-%m-%d %H:%M"))

    # ── Stocks
    sp500_tickers = get_sp500_tickers()
    stock_results = process_assets_in_batch(sp500_tickers, "stock", days=MA_DAYS)
    
    # ── Crypto
    crypto_tickers = get_crypto_tickers()
    crypto_results = process_assets_in_batch(crypto_tickers, "crypto", days=MA_DAYS)
    
    # -- Process and sort results
    def sort_and_categorize(results):
        below, above = [], []
        for res in results:
            dist = res['dist_pct']
            row = (res['ticker'], res['price'], res['ma'], dist, res['slope'])
            if 0 <= dist <= 1.0:
                below.append(row)
            elif -1.5 <= dist < 0:
                above.append(row)
        below.sort(key=lambda x: x[3])
        above.sort(key=lambda x: abs(x[3]))
        return below, above

    stocks_below, stocks_above = sort_and_categorize(stock_results)
    crypto_below, crypto_above = sort_and_categorize(crypto_results)
    print(f"\n[INFO] Stocks: Found {len(stocks_below)} below MA, {len(stocks_above)} above MA.")
    print(f"[INFO] Crypto: Found {len(crypto_below)} below MA, {len(crypto_above)} above MA.")

    # ── Build & Send Report
    total_results = len(stocks_below) + len(stocks_above) + len(crypto_below) + len(crypto_above)
    if total_results > 0:
        print(f"\n[INFO] Found {total_results} matching assets. Building report...")
        
        html_body = f"<!DOCTYPE html><html><head><meta charset='utf-8'>{BASE_STYLE}</head><body>"
        html_body += f"<h2 style='text-align:right; margin-right:24px;'>דוח סורק ממוצע נע {MA_DAYS} - {datetime.now().strftime('%d/%m/%Y')}</h2>"
        html_body += make_table(stocks_below, f"מניות מתחת לממוצע (עד 1%)")
        html_body += make_table(stocks_above, f"מניות מעל הממוצע (עד 1.5%)")
        html_body += make_table(crypto_below, f"קריפטו מתחת לממוצע (עד 1%)")
        html_body += make_table(crypto_above, f"קריפטו מעל הממוצע (עד 1.5%)")
        html_body += "</body></html>"

        display(HTML(html_body))
        send_email(f"Scanner Results MA{MA_DAYS} - {datetime.now().strftime('%d-%m-%Y')}", html_body)
    else:
        print("\n[INFO] No matching assets found. No email sent.")

if __name__ == "__main__":
    main()

