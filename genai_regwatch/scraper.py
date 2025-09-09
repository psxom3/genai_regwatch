import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from .db import db_connect, check_if_exists, save_metadata
from .utils import compute_hash, save_file_locally
from .config import RBI_NOTIFICATIONS_URL

ALLOWED_EXTENSIONS = (".pdf", ".htm", ".html", ".xls", ".xlsx", ".csv", ".docx")

def scrape_rbi_notifications():
    print("[START] Scraping RBI notifications...")
    response = requests.get(RBI_NOTIFICATIONS_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    conn = db_connect()
    cursor = conn.cursor()

    # RBI notifications are usually in a table → rows contain date + link
    rows = soup.select("table tr")  
    for row in rows:
        cols = row.find_all("td")
        if not cols or len(cols) < 2:
            continue

        # First column = date, Second column = link/title
        date_text = cols[0].get_text(strip=True)
        link = cols[1].find("a")

        if not link:
            continue

        href = link.get("href")

        # UPDATED SECTION: extract clean human-readable title
        raw_title = cols[1].get_text(" ", strip=True)

        # Remove trailing "XXX kb" (file size)
        if raw_title.lower().endswith("kb"):
            parts = raw_title.split()
            if len(parts) >= 2 and parts[-2].isdigit() and parts[-1].lower() == "kb":
                title = " ".join(parts[:-2])  # drop "260 kb"
            else:
                title = raw_title
        else:
            title = raw_title

        # If still empty, fallback to filename
        if not title.strip():
            title = os.path.basename(href) or "Untitled"
        # END UPDATE

        # Parse RBI date → fallback to today if fails
        try:
            pub_date = datetime.strptime(date_text, "%b %d, %Y").date()
        except Exception:
            pub_date = datetime.utcnow().date()

        # Debug print
        print("[DEBUG] Found:", href, "| Title:", title, "| Date:", pub_date)

        if not href:
            continue

        # allow extensions OR RBI dynamic notifications
        if not (href.lower().endswith(ALLOWED_EXTENSIONS) or "NotificationUser.aspx" in href):
            continue

        full_url = "https://rbi.org.in" + href if href.startswith("/") else href

        try:
            file_resp = requests.get(full_url)
            file_content = file_resp.content
            file_hash = compute_hash(file_content)

            if check_if_exists(cursor, file_hash):
                print(f"[SKIP] Old document: {title}")
                continue

            ext = os.path.splitext(href)[1].lower() or ".pdf"
            filename = f"{file_hash}{ext}"
            local_path = save_file_locally(file_content, filename)

            # save with real RBI pub_date
            save_metadata(cursor, title, full_url, pub_date, file_hash, local_path)

            print(f"[NEW] Saved: {title} → {local_path} | Date: {pub_date}")

        except Exception as e:
            print(f"Error processing {full_url}: {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("[DONE] Scraping complete.")













# import os
# import requests
# from bs4 import BeautifulSoup
# from datetime import datetime
# from .db import db_connect, check_if_exists, save_metadata
# from .utils import compute_hash, save_file_locally
# from .config import RBI_NOTIFICATIONS_URL

# ALLOWED_EXTENSIONS = (".pdf", ".htm", ".html", ".xls", ".xlsx", ".csv", ".docx")

# def scrape_rbi_notifications():
#     print("[START] Scraping RBI notifications...")
#     response = requests.get(RBI_NOTIFICATIONS_URL)
#     soup = BeautifulSoup(response.text, "html.parser")

#     conn = db_connect()
#     cursor = conn.cursor()

#     # RBI notifications are usually in a table → rows contain date + link
#     rows = soup.select("table tr")  # try to capture rows
#     for row in rows:
#         cols = row.find_all("td")
#         if not cols or len(cols) < 2:
#             continue

#         # First column = date, Second column = link/title
#         date_text = cols[0].get_text(strip=True)
#         link = cols[1].find("a")

#         if not link:
#             continue

#         href = link.get("href")

#         # 🔹 UPDATED SECTION: Clean title (remove trailing "xxx kb")
#         raw_title = cols[1].get_text(" ", strip=True)
#         if raw_title.lower().endswith("kb"):
#             parts = raw_title.split()
#             if len(parts) > 2:
#                 title = " ".join(parts[:-2])  # drop "237 kb"
#             else:
#                 title = raw_title
#         else:
#             title = raw_title

#         if not title or title.lower().endswith("kb"):
#             title = os.path.basename(href) or "Untitled"
#         # 🔹 END UPDATED SECTION

#         # Parse RBI date → fallback to today if fails
#         try:
#             pub_date = datetime.strptime(date_text, "%b %d, %Y").date()
#         except Exception:
#             pub_date = datetime.utcnow().date()

#         # Debug print
#         print("[DEBUG] Found:", href, "| Title:", title, "| Date:", pub_date)

#         if not href:
#             continue

#         # allow extensions OR RBI dynamic notifications
#         if not (href.lower().endswith(ALLOWED_EXTENSIONS) or "NotificationUser.aspx" in href):
#             continue

#         full_url = "https://rbi.org.in" + href if href.startswith("/") else href

#         try:
#             file_resp = requests.get(full_url)
#             file_content = file_resp.content
#             file_hash = compute_hash(file_content)

#             if check_if_exists(cursor, file_hash):
#                 print(f"[SKIP] Old document: {title}")
#                 continue

#             ext = os.path.splitext(href)[1].lower() or ".pdf"
#             filename = f"{file_hash}{ext}"
#             local_path = save_file_locally(file_content, filename)

#             # ✅ Save metadata with cleaned title + RBI pub_date
#             save_metadata(cursor, title, full_url, pub_date, file_hash, local_path)

#             print(f"[NEW] Saved: {title} → {local_path} | Date: {pub_date}")

#         except Exception as e:
#             print(f"Error processing {full_url}: {e}")

#     conn.commit()
#     cursor.close()
#     conn.close()
#     print("[DONE] Scraping complete.")
