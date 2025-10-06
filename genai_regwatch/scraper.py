import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil import parser
from playwright.sync_api import sync_playwright
from .db import db_connect, check_if_exists
from .utils import compute_hash, save_file_locally
from .config import RBI_NOTIFICATIONS_URL, NHB_NOTIFICATIONS_URL
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ALLOWED_EXTENSIONS = (".pdf", ".htm", ".html", ".xls", ".xlsx", ".csv", ".docx")


# ---------------------------------------------------
# Helper: save metadata with regulator param (RBI/NHB)
# ---------------------------------------------------
def save_metadata_for_regulator(cursor, regulator, title, url, pub_date, url_hash, local_path):
    if isinstance(pub_date, datetime):
        pub_date = pub_date.date()
    from datetime import datetime as dt
    cursor.execute(
        """
        INSERT INTO reg_updates 
        (regulator, title, url, pub_date, hash, raw_file_path, status, inserted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (regulator, title, url, pub_date, url_hash, local_path, "NEW", dt.utcnow())
    )


# ---------------------------------------------------
# Helper: extract a date from text or URL
# ---------------------------------------------------
def extract_date_from_text_or_url(text: str, url: str):
    """
    Tries to parse a date from either the anchor text or the URL.
    Falls back to today's date if nothing is found.
    """
    pub_date = datetime.utcnow().date()

    # Try text-based date
    try:
        pub_date = parser.parse(text, fuzzy=True).date()
        return pub_date
    except Exception:
        pass

    # Try URL-based date (patterns like DDMMYYYY or YYYY-MM-DD)
    try:
        date_patterns = [
            r"(\d{2}[/-]\d{2}[/-]\d{4})",  # 29-09-2025 or 29/09/2025
            r"(\d{8})",                    # 20250929
            r"(\d{4}[/-]\d{2}[/-]\d{2})"   # 2025-09-29
        ]
        for pattern in date_patterns:
            m = re.search(pattern, url)
            if m:
                return parser.parse(m.group(1), fuzzy=True).date()
    except Exception:
        pass

    return pub_date


# ---------------------------------------------------
# RBI Scraper
# ---------------------------------------------------
def scrape_rbi_notifications(force: bool = False):
    print("[START] Scraping RBI notifications...")
    response = requests.get(RBI_NOTIFICATIONS_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    conn = db_connect()
    cursor = conn.cursor()

    rows = soup.select("table tr")
    for row in rows:
        cols = row.find_all("td")
        if not cols or len(cols) < 2:
            continue

        date_text = cols[0].get_text(strip=True)
        link = cols[1].find("a")
        if not link:
            continue
        href = link.get("href")

        # Title cleaning
        raw_title = cols[1].get_text(" ", strip=True)
        if raw_title.lower().endswith("kb"):
            parts = raw_title.split()
            if len(parts) >= 2 and parts[-2].isdigit() and parts[-1].lower() == "kb":
                title = " ".join(parts[:-2])
            else:
                title = raw_title
        else:
            title = raw_title
        if not title.strip():
            title = os.path.basename(href) or "Untitled"

        # Date
        try:
            pub_date = datetime.strptime(date_text, "%b %d, %Y").date()
        except Exception:
            pub_date = datetime.utcnow().date()

        print("[DEBUG][RBI]", href, "| Title:", title, "| Date:", pub_date)

        if not href:
            continue
        if not (href.lower().endswith(ALLOWED_EXTENSIONS) or "NotificationUser.aspx" in href):
            continue

        full_url = "https://rbi.org.in" + href if href.startswith("/") else href
        try:
            file_resp = requests.get(full_url)
            file_content = file_resp.content
            file_hash = compute_hash(file_content)

            if not force and check_if_exists(cursor, file_hash):
                print(f"[SKIP] Old document (RBI): {title}")
                continue

            ext = os.path.splitext(href)[1].lower() or ".pdf"
            filename = f"{file_hash}{ext}"
            local_path = save_file_locally(file_content, filename)

            save_metadata_for_regulator(cursor, "RBI", title, full_url, pub_date, file_hash, local_path)
            print(f"[NEW] Saved (RBI): {title} → {local_path}")

        except Exception as e:
            print(f"[ERROR][RBI] {full_url}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("[DONE] Scraping RBI complete.")


# ---------------------------------------------------
# NHB Scraper (Playwright + date extraction + relaxed filtering)
# ---------------------------------------------------
def scrape_nhb_notifications(force: bool = False):
    """
    Scrapes NHB 'What's New' page using Playwright.
    Targets actual notice blocks with 'Download in English' links.
    """
    print("[START] Scraping NHB notifications (Playwright)...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(NHB_NOTIFICATIONS_URL, timeout=90000)  # allow more load time

            # Try waiting for multiple possible containers
            try:
                page.wait_for_selector("div.whats-new-content, div.col-md-12", timeout=60000)
            except Exception:
                print("[WARN] Primary selector not found, using fallback wait...")
                page.wait_for_timeout(5000)  # wait 5s as fallback

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        print(f"[ERROR] Failed to load NHB page with Playwright: {e}")
        return

    conn = db_connect()
    cursor = conn.cursor()
    found = 0

    # Notices usually inside cards/boxes under .whats-new-content
    notice_blocks = soup.select("div.whats-new-content div, div.col-md-12 div")
    print(f"[DEBUG][NHB] Total candidate blocks: {len(notice_blocks)}")

    for block in notice_blocks:
        # Skip if no "Download" button inside
        download_link = block.find("a", string=lambda s: s and "Download" in s)
        if not download_link:
            continue

        href = download_link.get("href", "").strip()
        if not href:
            continue

        # Build absolute URL
        if href.startswith("/"):
            full_url = "https://www.nhb.org.in" + href
        elif href.startswith("http"):
            full_url = href
        else:
            full_url = "https://www.nhb.org.in/" + href

        if not full_url.lower().endswith(ALLOWED_EXTENSIONS):
            continue

        # Title & date
        text = block.get_text(" ", strip=True)
        title = text.split("Download")[0].strip() or os.path.basename(full_url)
        pub_date = extract_date_from_text_or_url(text, full_url)

        try:
            file_resp = requests.get(full_url, verify=False, timeout=60)
            file_content = file_resp.content
            file_hash = compute_hash(file_content)

            if not force and check_if_exists(cursor, file_hash):
                print(f"[SKIP] Old NHB document: {title}")
                continue

            ext = os.path.splitext(full_url)[1].lower() or ".pdf"
            filename = f"{file_hash}{ext}"
            local_path = save_file_locally(file_content, filename)

            save_metadata_for_regulator(cursor, "NHB", title, full_url, pub_date, file_hash, local_path)
            print(f"[NEW] Saved (NHB): {title} | Date: {pub_date} | File: {local_path}")
            found += 1

        except Exception as e:
            print(f"[ERROR] Processing NHB {full_url}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print(f"[DONE] NHB scraping complete. New docs: {found}")


