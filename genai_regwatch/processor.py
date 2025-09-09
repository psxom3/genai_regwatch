import fitz  # PyMuPDF
from datetime import datetime
from langchain_openai import ChatOpenAI
from .db import db_connect
from .utils import read_file
from .alerts import send_email_alert
import json
import re

# ---------------------------- PDF Text Extraction ----------------------------
def extract_text_from_pdf(pdf_bytes):
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text

# ---------------------------- Updated: Multi-file extraction ----------------------------
def extract_text(file_bytes, filename):  # <--- NEW
    ext = filename.lower().split(".")[-1]
    if ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in ["htm", "html"]:
        from bs4 import BeautifulSoup
        return BeautifulSoup(file_bytes, "html.parser").get_text()
    elif ext in ["xls", "xlsx"]:
        import pandas as pd
        import io
        df = pd.read_excel(io.BytesIO(file_bytes))
        return df.to_string()
    elif ext == "csv":
        import pandas as pd
        import io
        df = pd.read_csv(io.BytesIO(file_bytes))
        return df.to_string()
    elif ext == "docx":
        from docx import Document
        import io
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    else:
        return ""

# ---------------------------- Summarization ----------------------------
def summarize_doc(text, title):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = f"Summarize the following RBI notification titled '{title}' in under 200 words, focusing on key regulatory changes.\n\n{text}"
    result = llm.invoke(prompt)
    return result.content  # ✅ extract string


# ---------------------------- Action Extraction (JSON-safe) ----------------------------
def extract_actions(text, title):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = f"""
    Extract compliance action points from the following RBI notification titled '{title}'.
    Return **pure JSON** with fields: function, task, due_by, references.

    Text:
    {text}
    """
    result = llm.invoke(prompt)
    return clean_json_string(result.content)  # ✅ pass only the text


def clean_json_string(json_str):
    # ---------------------------- Updated ----------------------------
    cleaned = re.sub(r"```.*?\n", "", json_str, flags=re.DOTALL)  # remove markdown/code block
    cleaned = cleaned.replace("```", "").strip()

    try:
        parsed = json.loads(cleaned)
        return json.dumps(parsed)  # re-serialize to string
    except Exception as e:
        print(f"[WARN] Failed to parse JSON from LLM output: {e}")
        return "{}"

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

# ---------------------------- Main Processing Loop ----------------------------
def process_new_docs():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, raw_file_path FROM reg_updates WHERE status = 'NEW'")
    new_docs = cursor.fetchall()

    for doc_id, title, file_path in new_docs:
        print(f"[PROCESS] Handling {title}")
        file_bytes = read_file(file_path)

        # ---------------------------- Updated ----------------------------
        text = extract_text(file_bytes, file_path)  # <--- uses updated multi-file extractor

        summary = summarize_doc(text, title)
        actions = extract_actions(text, title)

        save_summary_and_actions(cursor, doc_id, summary, actions)

        send_email_alert(title, summary, actions)

        cursor.execute("UPDATE reg_updates SET status = 'PROCESSED' WHERE id = %s", (doc_id,))
        conn.commit()
        print(f"[DONE] Processed {title}")

    cursor.close()
    conn.close()
