from flask import Flask, jsonify, request
import sqlite3
import os

app = Flask(__name__)

DB_FILE = "database.db"

# Initialize database if it doesn't exist
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Helper to add item
def add_item(value):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO items (value) VALUES (?)", (value,))
    conn.commit()
    conn.close()

# Helper to get all items
def get_items():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM items")
    items = [row[0] for row in c.fetchall()]
    conn.close()
    return items

# Routes
@app.route("/")
def home():
    return jsonify(get_items())

@app.route("/add", methods=["POST"])
def add():
    data = request.json
    if "value" not in data:
        return jsonify({"error": "Missing 'value'"}), 400
    add_item(data["value"])
    return jsonify(get_items())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    app.run(host="0.0.0.0", port=port)
