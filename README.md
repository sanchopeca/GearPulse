# GearPulse: AI-Powered Music Gear Deal Finder

GearPulse is an automation tool that monitors a major Serbian online marketplace for the latest music gear listings and uses **Gemini AI** to identify "Diamond Deals" — listings priced significantly below both Serbian retail and European used market averages.

## Key Features

- **Real-time Monitoring:** Scrapes multiple categories for today's newest listings:
  - Moduli i Sempleri
  - DJ Oprema
  - Klavijature, Oprema i Delovi
- **AI Valuation Expert:** Uses Gemini 2.0 Flash to batch-analyze gear value based on global market data (Reverb/eBay) and local retail pricing.
- **Realistic Browser Automation:** Uses `playwright-stealth` for natural browsing behavior.
- **Instant Alerts:** Sends detailed deal reports directly to your Telegram.
- **Scheduled Runs:** Runs daily via GitHub Actions cron, with manual trigger available from the GitHub UI.

## Getting Started

### 1. Prerequisites

- **Python 3.10+**
- **Gemini API Key:** Obtain from Google AI Studio.
- **Telegram Bot:** Create via @BotFather.

### 2. Installation

```bash
git clone https://github.com/YOUR_USERNAME/GearPulse.git
cd GearPulse

pip install -r requirements.txt
playwright install chromium
```

### 3. Environment Variables

Add these to your GitHub Repository Secrets (Settings > Secrets and variables > Actions):

| Variable             | Description                                |
| -------------------- | ------------------------------------------ |
| `BASE_URL`           | Base URL of the marketplace to scrape      |
| `GEMINI_API_KEY`     | Google Gemini API key                      |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather                      |
| `TELEGRAM_CHAT_ID`   | Your Telegram chat ID for receiving alerts |

For local development, create a `.env` file with the same variables.

## Usage

```bash
python scraper.py
```

The scraper runs automatically every day at 12:00 PM (Serbia time) via GitHub Actions. You can also trigger it manually from the Actions tab in GitHub using `workflow_dispatch`.

## How It Works

```
Daily cron (GitHub Actions) ──▶ python scraper.py ──▶ Scrape 3 categories ──▶ Gemini AI ──▶ Telegram alerts
```

### AI Deal Logic

1. **EU Base:** Calculates the global used average from Reverb/eBay sold listings.
2. **Serbian Markup:** NEW items use EU Base + 25%; USED items use EU Base + 15%.
3. **Deal Criteria:**
   - NEW: flagged if price is < 75% of Serbian retail.
   - USED: flagged if price is < 85% of Serbian used average.
   - **Diamond Deal:** price is also below EU used base.

## Tech Stack

- **Language:** Python 3.10
- **Scraper:** Playwright (Chromium) + Playwright-Stealth
- **AI Engine:** Google GenAI (Gemini 2.0 Flash)
- **Notifications:** Telegram Bot API
- **Automation:** GitHub Actions (daily cron + manual dispatch)

## License

For educational and personal use. Please respect terms of service of the monitored websites.
