import json
import requests
from bs4 import BeautifulSoup
from datetime import date
import os
import time

def scrape_page(url, title, college, category, section=""):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xhtml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  ERROR fetching {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove junk tags
    for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)

    # Basic cleanup (collapse extra whitespace)
    text = " ".join(text.split())

    if len(text) < 100:
        print(f"  WARNING: very little text scraped from {url} — check this page manually")

    return {
        "text": text,
        "source": url,
        "title": title,
        "college": college,
        "category": category,
        "section": section,
        "scraped_date": str(date.today())
    }

def save_documents(documents, category):
    folder = f"data/raw/{category}"
    os.makedirs(folder, exist_ok=True)
    filepath = f"{folder}/{category}.json"
    with open(filepath, "w") as f:
        json.dump(documents, f, indent=2)
    print(f"\nSaved {len(documents)} documents to {filepath}")

# ---------------------------------------------------------------
# THIS IS THE ONLY PART YOU NEED TO EDIT
# Add one entry per page you want to scrape
# Make sure college and category match the controlled vocabulary
# in the README exactly
# ---------------------------------------------------------------

pages_to_scrape = [
    {
        "url": "https://www.ccny.cuny.edu/financialaid",
        "title": "Test City College",
        "college": "City College",
        "category": "financial_aid",
        "section": ""
    },
]

# ---------------------------------------------------------------
# DO NOT MODIFY BELOW THIS LINE
# ---------------------------------------------------------------

if __name__ == "__main__":
    if not pages_to_scrape:
        print("No pages to scrape. Fill in pages_to_scrape first.")
        exit()

    category = pages_to_scrape[0]["category"]

    documents = []
    for page in pages_to_scrape:
        print(f"Scraping: {page['url']}")
        doc = scrape_page(**page)
        if doc:
            documents.append(doc)
        time.sleep(1)

    print(f"\nSuccessfully scraped {len(documents)}/{len(pages_to_scrape)} pages")
    save_documents(documents, category)