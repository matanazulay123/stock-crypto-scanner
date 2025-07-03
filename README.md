
---

# 📊 Stock & Crypto Scanner

## 👤 About the Project

I built this tool out of a personal need to **spot assets (stocks and cryptocurrencies) that might soon become good buying opportunities**.
It’s designed to be simple, fast, and easy to understand – even if you’re not an expert in finance or programming.

This project was created as a personal learning challenge, and it's perfect for:
- Beginners who want to explore Python through real-world data.
- Investors looking for a lightweight way to get market signals.
- Anyone who wants a starting point for automating financial tasks.

---

## 💡 What does it do?

This script scans:
-  **Top 500 U.S. stocks (S&P 500)**.
-  **A pre-defined list of major cryptocurrencies** that you can easily customize.

It fetches all market data in **highly efficient batches**, making the entire scan complete in under a minute.

For each asset, it checks if the current price is **close to its recent average price** (specifically, the 150-day moving average). This is a common method some investors use to spot when assets might be undervalued or ready for a potential move.

If any assets match the criteria, the script:
- Generates a clean, modern HTML table report.
- Sends that table as an email.
- If no assets match, it prints a simple message and does not send an email.

---

## ⚙️ How to Use It

### 1. Install Required Packages
First, you need to install the necessary Python libraries.
```bash
pip install yfinance pandas ipython
```

### 2. Configure Your Credentials
For security, your Gmail App Password is not stored in the script. You need to set it as an environment variable.

**On Windows (in Command Prompt):**
```cmd
setx GMAIL_APP_PASSWORD "your_gmail_app_password_here"
```

💡 **Important:** Make sure you're using a **Gmail App Password**, not your regular account password. You can generate one from your Google Account security settings.

### 3. Configure Emails in the Script
Open the script file (`scanner.py` or similar) and update the following lines at the top with your email addresses:
```python
RECIPIENT_EMAIL   = "matanazul23@gmail.com"  # The address to send the report TO
SENDER_EMAIL      = "matanazul23@gmail.com"    # Your Gmail address
```

### 4. Run the Scanner
You're all set! Run the script from your terminal:
```bash
python scanner.py
```
The script will print its progress and send an email if it finds any matching assets.

---

## 🛠️ Customization

### How to Change the List of Cryptocurrencies
The list of cryptocurrencies to be scanned is hard-coded directly in the script for easy access. To edit it, find the `get_crypto_tickers()` function and modify the list inside:

```python
def get_crypto_tickers() -> list[str]:
    """
    Returns the list of crypto tickers for yfinance.
    """
    raw_tickers = [
        # EDIT THIS LIST TO ADD OR REMOVE COINS
        'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'TRX', 'DOGE', 'ADA', ...
    ]
    
    # The code automatically adds '-USD' to each ticker
    return [f"{ticker.upper()}-USD" for ticker in raw_tickers]
```

---

## 🚀 Tech Stack

- **Python**
- **yfinance**: For fetching all stock and cryptocurrency market data efficiently.
- **pandas**: For powerful and fast data manipulation.
- **smtplib**: The standard Python library for sending emails.
- **HTML & CSS**: For creating a modern and readable email report.
