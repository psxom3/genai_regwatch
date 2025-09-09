import gradio as gr
import psycopg2
import pandas as pd
from dotenv import load_dotenv
import os
import json
from main import run_pipeline

# ---- DB CONFIG ----
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# ---- HELPERS ----
def fetch_updates(limit=10):
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    query = """
        SELECT id, regulator, title, url, pub_date, status, inserted_at
        FROM reg_updates
        ORDER BY inserted_at DESC
        LIMIT %s;
    """
    df = pd.read_sql(query, conn, params=(limit,))
    conn.close()
    return df

def fetch_summaries(limit=10):
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    query = """
        SELECT id, update_id, exec_summary, created_at
        FROM reg_summaries
        ORDER BY created_at DESC
        LIMIT %s;
    """
    df = pd.read_sql(query, conn, params=(limit,))
    conn.close()
    return df


def fetch_actions(limit=10):
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    query = """
        SELECT id, update_id, actions_json, created_at
        FROM reg_actions
        ORDER BY created_at DESC
        LIMIT %s;
    """
    df = pd.read_sql(query, conn, params=(limit,))
    conn.close()

    # Convert JSON field to readable text
    df["actions_json"] = df["actions_json"].apply(
        lambda x: json.dumps(x, indent=2, ensure_ascii=False) if isinstance(x, (dict, list)) else str(x)
    )

    return df


def trigger_pipeline_with_status():
    # Step 1: show message immediately
    yield "⏳ Running pipeline... please wait", None, None, None  

    # Step 2: run pipeline
    run_pipeline()

    # Step 3: fetch results from DB
    updates = fetch_updates()
    summaries = fetch_summaries()
    actions = fetch_actions()

    # Step 4: return final results
    yield "✅ Pipeline finished!", updates, summaries, actions


# ---- GRADIO UI ----
with gr.Blocks() as demo:
    gr.Markdown("# 🏦 RBI Regulatory Watch")
    gr.Markdown("Scrape RBI updates, view summaries & action items.")

    
    
    with gr.Tab("🔄 Run Pipeline"):
        run_btn = gr.Button("🚀 Run Scraper + Processor")
        status = gr.Textbox(label="Status", interactive=False)

        updates_table = gr.DataFrame(interactive=False, label="Updates")
        summaries_table = gr.DataFrame(interactive=False, label="Summaries")
        actions_table = gr.DataFrame(interactive=False, label="Actions")

        run_btn.click(
            fn=trigger_pipeline_with_status,
            outputs=[status, updates_table, summaries_table, actions_table]
        )


    with gr.Tab("📑 Updates"):
        refresh_updates_btn = gr.Button("Refresh Updates")
        updates_table2 = gr.DataFrame(interactive=False)
        refresh_updates_btn.click(fn=fetch_updates, outputs=updates_table2)

    with gr.Tab("📝 Summaries"):
        refresh_summaries_btn = gr.Button("Refresh Summaries")
        summaries_table2 = gr.DataFrame(interactive=False)
        refresh_summaries_btn.click(fn=fetch_summaries, outputs=summaries_table2)

    with gr.Tab("✅ Actions"):
        refresh_actions_btn = gr.Button("Refresh Actions")
        actions_table2 = gr.DataFrame(interactive=False)
        refresh_actions_btn.click(fn=fetch_actions, outputs=actions_table2)

if __name__ == "__main__":
    demo.launch()
