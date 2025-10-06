from genai_regwatch import scraper, processor

def run_pipeline():
    """Run the full scraping + processing pipeline for RBI and NHB."""
    print("[START] Scraping RBI notifications...")
    scraper.scrape_rbi_notifications()
    print("[DONE] Scraping RBI complete.")

    print("[START] Scraping NHB notifications...")
    scraper.scrape_nhb_notifications()
    print("[DONE] Scraping NHB complete.")

    print("[START] Processing new documents...")
    processor.process_new_docs()
    print("[DONE] Processing complete.")

if __name__ == "__main__":
    run_pipeline()
