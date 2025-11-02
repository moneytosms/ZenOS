"""Inspect and add missing columns to the courses table in data/zenos.db

This script checks for `start_date` and `end_date` columns in the `courses` table.
If they are missing it runs `ALTER TABLE ADD COLUMN` for each missing column.
It prints the schema before and after changes.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "zenos.db")

def get_columns(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def add_column_if_missing(conn, table, column_name, column_def):
    cols = get_columns(conn, table)
    if column_name in cols:
        print(f"Column '{column_name}' already exists in '{table}'.")
        return False
    print(f"Adding column '{column_name}' to '{table}' as: {column_def}")
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_def}")
    return True


def main():
    print("DB_PATH:", DB_PATH)
    if not os.path.exists(DB_PATH):
        print("Database file not found at", DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        print("Columns before:", get_columns(conn, 'courses'))
        changed = False
        # Define the column SQL types to mirror SQLAlchemy Date -> DATE
        changed |= add_column_if_missing(conn, 'courses', 'start_date', 'DATE')
        changed |= add_column_if_missing(conn, 'courses', 'end_date', 'DATE')
        # Add skipped_classes integer column if missing
        changed |= add_column_if_missing(conn, 'courses', 'skipped_classes', 'INTEGER DEFAULT 0')
        if changed:
            conn.commit()
            print("Committed schema changes.")
        else:
            print("No schema changes required.")
        print("Columns after:", get_columns(conn, 'courses'))

        # Optional quick SELECT to ensure table is queryable
        cur = conn.execute('SELECT id, user_id, name, start_date, end_date FROM courses LIMIT 5')
        rows = cur.fetchall()
        print(f"Sample rows (up to 5): {rows}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
