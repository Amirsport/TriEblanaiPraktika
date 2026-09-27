import json
import math
import sqlite3
import argparse
from contextlib import contextmanager
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.parse 
ROOT = Path(__file__).parent.parent
FRONT = ROOT / "front"
DEVICES = ("watering", "ventilation")
DEFAULT_SETTINGS = {
    "moisture_target": 0.0,
}

@contextmanager
def connect(database):
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def initialize(database):
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    with connect(database) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                moisture REAL NOT NULL CHECK(moisture >= 0 AND moisture <= 100),
                recorded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                temperature REAL,
            );
            create table IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                moisture_target REAL NOT NULL,
                value TEXT
            );
            create table IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message TEXT
            );
            create table IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            );
            create table IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL CHECK(enabled IN (0,1))
            );
        """)
        db.execute("INSERT OR IGNORE INTO settings (id, moisture_target) VALUES (1, ?, ?)",
                    tuple(DEFAULT_SETTINGS.values()))
        db.executemany("INSERT OR IGNORE INTO devices (name, enabled) VALUES (?, ?)",
                       [(device, 1) for device in DEVICES])


# Способ создания сервера. Надо додумать...

#def create_server(host="127.0.0.1", port=8000, database=None):
#    database = Path(database) if database else ROOT / "data" / "greenhouse.sqlite3"
#    initialize(database)
#    server = ThreadingHTTPServer((host, port), Handler)
#   server.database = database
#    return server


#def main():
#    parser = argparse.ArgumentParser(description="Greenhouse local server")
#    parser.add_argument("--host", default="127.0.0.1")
#    parser.add_argument("--port", type=int, default=8000)
#    parser.add_argument("--db", type=Path, default=ROOT / "data" / "greenhouse.sqlite3")
#    args = parser.parse_args()
#    server = create_server(args.host, args.port, args.db)
#    print(f"Greenhouse: http://{args.host}:{server.server_port}", flush=True)
#    try:
#        server.serve_forever()
#    except KeyboardInterrupt:
#        pass
#    finally:
#        server.server_close()


#if __name__ == "__main__":
#    main()

