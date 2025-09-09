import psycopg2
from datetime import datetime, date   
from .config import DB_CONFIG

def db_connect():
    return psycopg2.connect(**DB_CONFIG)

def check_if_exists(cursor, url_hash):
    cursor.execute("SELECT 1 FROM reg_updates WHERE hash = %s", (url_hash,))
    return cursor.fetchone() is not None

def save_metadata(cursor, title, url, pub_date, url_hash, local_path):
    # to Ensure pub_date is a proper date
    if isinstance(pub_date, datetime):
        pub_date = pub_date.date()
    elif not isinstance(pub_date, date):
        pub_date = datetime.utcnow().date()

    cursor.execute(
        """
        INSERT INTO reg_updates 
        (regulator, title, url, pub_date, hash, raw_file_path, status, inserted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        ("RBI", title, url, pub_date, url_hash, local_path, "NEW", datetime.utcnow())
    )
