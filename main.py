from genai_regwatch import scraper, processor

def run_pipeline():
    """Run the full scraping + processing pipeline."""
    print("[START] Scraping RBI notifications...")
    scraper.scrape_rbi_notifications()
    print("[DONE] Scraping complete.")

    print("[START] Processing new documents...")
    processor.process_new_docs()
    print("[DONE] Processing complete.")

if __name__ == "__main__":
    run_pipeline()
