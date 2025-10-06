import fitz  # PyMuPDF
from datetime import datetime
from .db import db_connect
from .utils import read_file
from .alerts import send_email_alert
import json, re, requests
from .config import OLLAMA_URL, OLLAMA_MODEL, MAX_WORKERS
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------- PDF Text Extraction ----------------------------
def extract_text_from_pdf(pdf_bytes):
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text

# ---------------------------- Multi-file extraction ----------------------------
def extract_text(file_bytes, filename):
    ext = filename.lower().split(".")[-1]
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in ["htm", "html"]:
        from bs4 import BeautifulSoup
        return BeautifulSoup(file_bytes, "html.parser").get_text()
    elif ext in ["xls", "xlsx"]:
        import pandas as pd, io
        df = pd.read_excel(io.BytesIO(file_bytes))
        return df.to_string()
    elif ext == "csv":
        import pandas as pd, io
        df = pd.read_csv(io.BytesIO(file_bytes))
        return df.to_string()
    elif ext == "docx":
        from docx import Document
        import io
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return ""

# ---------------------------- Text Cleaner ----------------------------
### NEW: Remove RBI/NHB boilerplate headers that confuse the LLM
def clean_rbi_headers(text: str) -> str:
    patterns = [
        r"बेटी बचाओ.*?\n",
        r"RESERVE BANK OF INDIA.*?\n",
        r"भारतीय.*?रज़वर् बैंक.*?\n",
        r"Department of .*?, Central Office.*?\n",
        r"Tel:.*?\n",
        r"Fax:.*?\n",
        r"Email.*?\n"
    ]
    for p in patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()

# ---------------------------- Text Chunking ----------------------------
def chunk_text(text, max_words=400):
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

# ---------------------------- Helper: call Ollama ----------------------------
def call_ollama(prompt, max_tokens=512, retries=2):
    api_url = OLLAMA_URL.rstrip("/") + "/api/generate"
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "max_tokens": max_tokens}

    for attempt in range(retries):
        try:
            resp = requests.post(api_url, json=payload, timeout=180, stream=True)
            resp.raise_for_status()

            final_output = ""
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                    if "response" in data:
                        final_output += data["response"]
                    elif "output" in data:
                        final_output += data["output"]
                except json.JSONDecodeError:
                    continue
            return final_output.strip() if final_output else "LLM_CALL_FAILED"

        except Exception as e:
            print(f"[WARN] Ollama call failed (attempt {attempt+1}): {e}")

    return "LLM_CALL_FAILED"

# ---------------------------- Summarization ----------------------------
def summarize_doc(text, title, actions_json=None):   
    text = clean_rbi_headers(text)   ### keep cleaning step
    chunks = chunk_text(text, 400)
    summaries = []

    for idx, chunk in enumerate(chunks, 1):
        prompt = f"""
You are a compliance assistant.
Summarize PART {idx} of the notification titled '{title}'.

Rules:
- Always produce a factual executive summary (max 120 words).
- Never refuse, never ask for more content.
- If the section is only headers or addresses, respond: "Administrative notice only — no compliance impact."
- If it is about bid/tender/meeting dates, highlight the key event and deadline.

Text:
{chunk}
"""
        result = call_ollama(prompt, max_tokens=300)
        if not result or "LLM_CALL_FAILED" in result:
            result = "No material content in this section."
        summaries.append(result)

    combined = "\n".join(summaries)

    # check if actions exist 
    has_actions = False
    try:
        if actions_json:   ### NEW: look at extracted actions
            cleaned_actions_json = clean_json_string(actions_json)
            parsed_actions = json.loads(cleaned_actions_json)
            if isinstance(parsed_actions, list) and len(parsed_actions) > 0:
                has_actions = True
    except Exception:
        pass
    

    if has_actions:   ### If actions exist → compliance-focused summary
        final_prompt = f"""
Combine the following partial summaries into one coherent executive summary (<200 words) 
for the notification '{title}'.

Ensure the output is factual, concise, and clearly reflects any regulatory obligations or compliance requirements.

Summaries:
{combined}
"""
    else:   ### fallback only if no actions
        final_prompt = f"""
Combine the following partial summaries into one coherent executive summary (<200 words) 
for the notification '{title}'.

Ensure the output is factual, concise, and never empty. 
If no compliance actions or obligations are identified across all parts, and the content is purely administrative (headers, dates, addresses, acknowledgements), state: 
"Administrative circular — no compliance action required."
Otherwise, summarize the key regulatory changes and obligations.

Summaries:
{combined}
"""

    final = call_ollama(final_prompt, max_tokens=400)
    return final if final and "LLM_CALL_FAILED" not in final else "No summary available."


# ---------------------------- Action Extraction ----------------------------
def extract_actions(text, title):
    text = clean_rbi_headers(text)   ### keep cleaning step
    chunks = chunk_text(text, 400)
    all_actions = []

    for idx, chunk in enumerate(chunks, 1):
        prompt = f"""
Extract compliance action points from PART {idx} of '{title}'.

Return strictly a JSON array of objects with keys: 
function, task, due_by, references.

Rules:
- If no compliance action, return [].
- Do not generate explanations or meta text.
- Focus only on concrete obligations for banks, ADs, or financial institutions.

Text:
{chunk}
"""
        result = call_ollama(prompt, max_tokens=300)
        if not result or "LLM_CALL_FAILED" in result:
            continue
        parsed = clean_json_string(result)
        try:
            all_actions.extend(json.loads(parsed))
        except Exception:
            continue

    return json.dumps(all_actions)


# ---------------------------- JSON Cleaner ----------------------------
def clean_json_string(json_str):
    cleaned = str(json_str).strip()
    cleaned = re.sub(r"```(?:json)?", "", cleaned).replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        return json.dumps(parsed)
    except Exception:
        m = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(1))
                return json.dumps(parsed)
            except Exception:
                return "[]"
    return "[]"

# ---------------------------- DB Saving ----------------------------
def save_summary_and_actions(cursor, doc_id, summary, actions):
    cursor.execute(
        "INSERT INTO reg_summaries (update_id, exec_summary, created_at) VALUES (%s, %s, %s)",
        (doc_id, summary, datetime.utcnow())
    )
    cursor.execute(
        "INSERT INTO reg_actions (update_id, actions_json, created_at) VALUES (%s, %s, %s)",
        (doc_id, actions, datetime.utcnow())
    )

# ---------------------------- Worker ----------------------------
def process_single_doc(doc_id, regulator, title, url, file_path):
    try:
        print(f"[PROCESS] Handling {title}")
        file_bytes = read_file(file_path)
        text = extract_text(file_bytes, file_path)

        # CHANGED ORDER ↓↓↓
        actions = extract_actions(text, title)                      
        summary = summarize_doc(text, title, actions_json=actions)  

        conn = db_connect()
        cursor = conn.cursor()
        save_summary_and_actions(cursor, doc_id, summary, actions)

        send_email_alert(regulator, title, url, summary, actions)

        cursor.execute("UPDATE reg_updates SET status = 'PROCESSED' WHERE id = %s", (doc_id,))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[DONE] Processed {title}")
    except Exception as e:
        print(f"[ERROR] Failed processing {title}: {e}")


# ---------------------------- Main ----------------------------
def process_new_docs():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, regulator, title, url, raw_file_path FROM reg_updates WHERE status = 'NEW'")
    new_docs = cursor.fetchall()
    cursor.close()
    conn.close()

    if not new_docs:
        print("[INFO] No new documents to process.")
        return

    print(f"[START] Processing {len(new_docs)} new documents with {MAX_WORKERS} workers...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_single_doc, doc_id, regulator, title, url, file_path)
                   for doc_id, regulator, title, url, file_path in new_docs]

        for f in as_completed(futures):
            f.result()

    print("[DONE] Parallel document processing complete.")

