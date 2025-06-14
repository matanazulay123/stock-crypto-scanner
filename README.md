# 📊 Stock & Crypto Scanner

## 👤 About the Project

I built this tool out of a personal need to **spot assets (stocks and cryptocurrencies) that might soon become good buying opportunities**.  
It’s designed to be simple to run, flexible, and easy to understand – even if you’re not an expert in finance or programming.

This project was created as a personal learning challenge, and it's perfect for:
- Beginners who want to explore Python through real-world data
- Investors looking for a lightweight way to get market signals
- Anyone who wants a starting point for automating financial tasks

---

## 💡 What does it do?

This script scans:
-  **Top 500 U.S. stocks (S&P 500)**
-  **Top cryptocurrencies (with market cap over $1B)**

For each asset, it checks if the current price is **close to its recent average price** (based on the last few months).  
This is a common method some investors use to spot when assets might be **undervalued or ready for a potential move**.

If any assets match the criteria, the script:
- Lists them in a clean HTML table
- Sends that table as an email report
- If no assets match, it prints a simple message instead

---

## 📧 How does the email work?

You configure your email once (securely), and the report gets sent automatically to the recipient you choose.  
You can run this script manually or schedule it to run daily for automatic updates.

---

## ⚙️ How to Use It

1. **Install required packages:**

```bash
pip install -r requirements.txt
```

2. **Create a `.env` file** in the same folder as `scanner.py` with the following content:

```env
SENDER_EMAIL=your_gmail_address
SENDER_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=recipient_address
```

 💡 Make sure you're using a Gmail **App Password**, not your regular password.

3. **Run the scanner:**

```bash
python scanner.py
```

---

## 🛠 Tech Stack

- Python 
- `yfinance` + `pandas` for stock data
- CoinGecko API for crypto prices
- `smtplib` for email sending
- HTML email formatting for better readability
