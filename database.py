import sqlite3
from contextlib import closing
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

# --- DATABASE SETUP ---
@st.cache_resource
def get_conn():
    conn = sqlite3.connect("stopwatch.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_conn()
    with closing(conn.cursor()) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                team TEXT NOT NULL,
                run_index INTEGER NOT NULL,
                elapsed_seconds REAL NOT NULL,
                saved_at TEXT NOT NULL
            )
        """)
        conn.commit()

def get_next_index(username: str) -> int:
    conn = get_conn()
    with closing(conn.cursor()) as cur:
        cur.execute("SELECT MAX(run_index) FROM times WHERE username = ?", (username,))
        result = cur.fetchone()[0]
        return (result or 0) + 1

def save_time(username: str, team: str, elapsed_seconds: float):
    run_index = get_next_index(username)
    conn = get_conn()
    with closing(conn.cursor()) as cur:
        cur.execute("""
            INSERT INTO times (username, team, run_index, elapsed_seconds, saved_at)
            VALUES (?, ?, ?, ?, ?)
        """, (username, team, run_index, elapsed_seconds, datetime.now(timezone.utc).isoformat()))
        conn.commit()

def load_times() -> pd.DataFrame:
    conn = get_conn()
    return pd.read_sql_query(
        """
        SELECT username, team, run_index, elapsed_seconds, saved_at
        FROM times
        ORDER BY team, elapsed_seconds ASC
        """,
        conn
    )

def delete_time(username: str, run_index: int):
    conn = get_conn()
    with closing(conn.cursor()) as cur:
        cur.execute("DELETE FROM times WHERE username = ? AND run_index = ?", (username, run_index))
        conn.commit()