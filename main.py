from flask import Flask, jsonify, request
import sqlite3
import os
import json

app = Flask(__name__)

DB_FILE = "database.db"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", None)  # Set in production


# -------------------------
# Database initialization
# -------------------------
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        # Items table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value TEXT NOT NULL
            )
        """)
        # Request logs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS request_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                headers TEXT,
                body TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


# -------------------------
# Database helpers
# -------------------------
def add_item(value):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("INSERT INTO items (value) VALUES (?)", (value,))


def get_items():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute("SELECT id, value FROM items")
        return [{"id": row[0], "value": row[1]} for row in cursor.fetchall()]


def delete_all_items():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM items")


def log_request(req):
    ip = req.headers.get("X-Forwarded-For", req.remote_addr)
    method = req.method
    path = req.path
    headers = json.dumps(dict(req.headers))
    body = json.dumps(req.json) if req.is_json else None

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            INSERT INTO request_logs (ip, method, path, headers, body)
            VALUES (?, ?, ?, ?, ?)
        """, (ip, method, path, headers, body))


def get_request_logs(limit=100):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute("""
            SELECT id, ip, method, path, headers, body, timestamp
            FROM request_logs
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        logs = [
            {
                "id": row[0],
                "ip": row[1],
                "method": row[2],
                "path": row[3],
                "headers": json.loads(row[4]) if row[4] else None,
                "body": json.loads(row[5]) if row[5] else None,
                "timestamp": row[6]
            }
            for row in cursor.fetchall()
        ]
    return logs


# Initialize DB
init_db()


# -------------------------
# Global request logger
# -------------------------
@app.before_request
def before_every_request():
    log_request(request)


# -------------------------
# Routes
# -------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify(get_items())


@app.route("/add", methods=["POST"])
def add():
    data = request.json or {}
    value = data.get("value")
    if not value:
        return jsonify({"error": "Missing 'value'"}), 400
    add_item(value)
    return jsonify(get_items())


# Admin: delete all items
@app.route("/admin/delete_all", methods=["POST"])
def admin_delete_all():
    token = request.headers.get("X-ADMIN-TOKEN")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    delete_all_items()
    return jsonify({"status": "All items deleted"})


# Admin: view request logs
@app.route("/admin/requests", methods=["GET"])
def admin_requests():
    token = request.headers.get("X-ADMIN-TOKEN")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    logs = get_request_logs(limit=100)
    return jsonify(logs)
@app.route("/admin/clear_logs", methods=["POST"])
def admin_clear_logs():
    token = request.headers.get("X-ADMIN-TOKEN")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM request_logs")
    return jsonify({"status": "All request logs cleared"})


# -------------------------
# Run server
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    app.run(host="0.0.0.0", port=port)
