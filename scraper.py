import os
import asyncio
import json
import requests
from google import genai
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Load secrets
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BASE_URL = os.getenv("BASE_URL")

client = genai.Client(api_key=GEMINI_KEY)

def analyze_ads_batch(ads_data):
    """Sends all ads to Gemini in one prompt for batch analysis."""
    # Convert list of dicts to a readable string for the AI
    ads_list_str = ""
    for i, ad in enumerate(ads_data):
        ads_list_str += f"ID: {i} | Item: {ad['title']} | Condition: {ad['condition']} | Price: {ad['price']} EUR\n"

    prompt = f"""
    You are a music gear valuation expert specializing in the Serbian market (a major Serbian online marketplace).
    Analyze the provided list and identify "Diamond Deals." 

    Ads List:
    {ads_list_str}

    Logic Rules:
    1. CONDITION CHECK: Determine if the item is NEW (unopened/store demo) or USED.
    
    2. ESTABLISH BASELINES:
       - EU BASE: Reference 'Sold' listings from Reverb/eBay for the same condition.
       - SRB RETAIL (For NEW): Calculated as (EU Base + 25%).
       - SRB USED AVG (For USED): Calculated as (EU Used Base + 15%). 
         *Note: Used gear is more expensive in Serbia than EU due to supply/customs.*

    3. THE DEAL CRITERIA:
       - If NEW: Flag 'YES' only if Scraped Price is < 75% of SRB RETAIL.
       - If USED: Flag 'YES' only if Scraped Price is < 85% of SRB USED AVG.
       - High Priority: If the price is also lower than the EU Used Base, it's a "Diamond Deal."

    Return your response as a JSON array of objects for ONLY the items that are "YES" deals. 
    If NO items are deals, return an empty array [].
    
    Format example:
    [
      {{
        "id": 0, 
        "result": "YES", 
        "condition": "USED",
        "reason": "SRB used avg is ~1150e, this is 850e. Below EU used prices too. Strong buy."
      }},
      {{
        "id": 5, 
        "result": "YES", 
        "condition": "NEW",
        "reason": "Retail at Player/Mitros is 500e, this is 320e. Significant savings."
      }}
    ]
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Batch AI Error: {e}")
        return []

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def clean_price(price_str):
    if not price_str or "dogovor" in price_str.lower(): return None
    numeric_part = "".join(filter(str.isdigit, price_str))
    if not numeric_part: return None
    val = int(numeric_part)
    if "din" in price_str.lower() or val > 5000:
        return round(val / 117.4)
    return val

async def scrape_page(category, page, captured_ads, seen_ad_ids, retries=3):
    url = f"{BASE_URL}/muzicki-instrumenti/{category}/pretraga?categoryId=22&groupId=791&currency=eur&period=today"

    for attempt in range(retries):
        try:
            await page.goto(url, wait_until="domcontentloaded")
            break
        except Exception as e:
            if attempt < retries - 1:
                print(f"Retry {attempt + 1}/{retries} for {category}: {e}")
                await asyncio.sleep(2)
            else:
                print(f"Failed to load {category} after {retries} attempts")
                return

    ad_selector = "[class*='AdItem_adOuterHolder']"
    await page.wait_for_selector(ad_selector, timeout=15000)
    ad_elements = await page.query_selector_all(ad_selector)

    for ad in ad_elements:
        try:
            ad_id = await ad.get_attribute("id")
            if ad_id in seen_ad_ids:
                continue
            seen_ad_ids.add(ad_id)

            title_el = await ad.query_selector("[class*='AdItem_name']")
            price_el = await ad.query_selector("[class*='AdItem_price']")
            cond_el = await ad.query_selector("[class*='AdItem_condition']")
            link_el = await ad.query_selector("a")

            title = await title_el.inner_text()
            price_eur = clean_price(await price_el.inner_text())
            condition = await cond_el.inner_text() if cond_el else "Polovno"
            link = BASE_URL + await link_el.get_attribute("href")

            if price_eur:
                captured_ads.append({
                    "title": title,
                    "price": price_eur,
                    "condition": "New" if "novo" in condition.lower() else "Used",
                    "link": link
                })
        except:
            continue

async def run_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        captured_ads = []
        seen_ad_ids = set()

        categories = ['moduli-i-sempleri', 'dj-oprema', 'klavijature-oprema-i-delovi']
        for i, category in enumerate(categories):
            await scrape_page(category, page, captured_ads, seen_ad_ids)
            if i < len(categories) - 1:
                await asyncio.sleep(2)  # delay between requests to avoid HTTP2 errors

        print(f"Collected {len(captured_ads)} ads. Sending to AI for batch analysis...")

        # 2. Analyze in one go
        deals = analyze_ads_batch(captured_ads)

        # 3. Send alerts only for the good deals
        for deal in deals:
            ad_idx = deal['id']
            original_ad = captured_ads[ad_idx]
            
            msg = f"💎 **DEAL FOUND** 💎\n\n" \
                  f"Item: {original_ad['title']}\n" \
                  f"Price: {original_ad['price']}€\n" \
                  f"AI Reason: {deal['reason']}\n\n" \
                  f"🔗 [Open Ad]({original_ad['link']})"
            
            send_telegram(msg)
            print(f"✅ Alert sent: {original_ad['title']}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_scraper())