"""Website lời chúc 20/10 dùng Python chuẩn + SQLite, không cần cài thư viện ngoài."""
from __future__ import annotations

import json
import mimetypes
import os
import re
import sqlite3
import socket
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "templates" / "index.html"
STATIC_DIR = BASE_DIR / "static"
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
DB_PATH = Path(os.environ.get("WISH_DB_PATH", str(INSTANCE_DIR / "wishes.sqlite3")))
HOST = "0.0.0.0"  # Always listen on all interfaces so phones on the same Wi-Fi can connect.
PORT = int(os.environ.get("PORT", "5000"))
MAX_BODY_BYTES = 16 * 1024

rate_lock = Lock()
recent_submissions: dict[str, list[float]] = {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_key TEXT NOT NULL UNIQUE,
            last_seen TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wishes_created_at ON wishes(created_at DESC)")


def clean_text(value: object, maximum: int) -> str:
    if not isinstance(value, str):
        return ""
    # Keep Vietnamese text and emoji; remove control characters and flatten newlines.
    value = "".join(ch for ch in value if ch in "\n\t" or ord(ch) >= 32)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:maximum]


def rate_limited(client_ip: str) -> bool:
    """Permit up to eight guestbook submissions from an IP within ten minutes."""
    now = time.time()
    with rate_lock:
        recent = [stamp for stamp in recent_submissions.get(client_ip, []) if now - stamp < 600]
        if len(recent) >= 8:
            recent_submissions[client_ip] = recent
            return True
        recent.append(now)
        recent_submissions[client_ip] = recent
        if len(recent_submissions) > 1000:
            cutoff = now - 600
            for key in list(recent_submissions):
                recent_submissions[key] = [stamp for stamp in recent_submissions[key] if stamp >= cutoff]
                if not recent_submissions[key]:
                    recent_submissions.pop(key, None)
        return False


class WebsiteHandler(BaseHTTPRequestHandler):
    server_version = "20OctMorphPython/1.1"

    def log_message(self, fmt: str, *args: object) -> None:
        # Avoid dumping submitted message bodies in the terminal log.
        super().log_message(fmt, *args)

    def send_bytes(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data: object, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_bytes(body, "application/json; charset=utf-8", status)

    def read_json(self) -> dict:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            length = 0
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValueError("Dữ liệu gửi lên quá lớn.")
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Dữ liệu gửi lên không hợp lệ.")
        if not isinstance(value, dict):
            raise ValueError("Dữ liệu gửi lên không hợp lệ.")
        return value

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/static/"):
            relative = Path(path.removeprefix("/static/"))
            candidate = (STATIC_DIR / relative).resolve()
            try:
                candidate.relative_to(STATIC_DIR.resolve())
            except ValueError:
                self.send_json({"error": "Không tìm thấy tệp."}, 404)
                return
            if not candidate.is_file():
                self.send_json({"error": "Không tìm thấy tệp."}, 404)
                return
            try:
                data = candidate.read_bytes()
            except OSError:
                self.send_json({"error": "Không đọc được tệp."}, 500)
                return
            content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            self.send_bytes(data, content_type, 200)
            return
        if path == "/" or path == "/index.html":
            try:
                body = TEMPLATE_PATH.read_bytes()
            except OSError:
                self.send_bytes(b"Website template is missing.", "text/plain; charset=utf-8", 500)
                return
            self.send_bytes(body, "text/html; charset=utf-8")
            return
        if path == "/health":
            self.send_json({"status": "ok", "app": "20-10-wishes-morph", "database": "sqlite"})
            return
        if path == "/api/guests":
            with get_db() as conn:
                rows = conn.execute("SELECT name, last_seen FROM guests ORDER BY last_seen DESC LIMIT 50").fetchall()
            self.send_json({"guests": [{"name": row["name"], "last_seen": row["last_seen"]} for row in rows]})
            return
        if path == "/api/wishes":
            with get_db() as conn:
                rows = conn.execute("SELECT name, message, created_at FROM wishes ORDER BY id DESC LIMIT 40").fetchall()
            self.send_json({"wishes": [{"name": row["name"], "message": row["message"], "created_at": row["created_at"]} for row in rows]})
            return
        self.send_json({"error": "Không tìm thấy đường dẫn."}, 404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in ("/api/guests", "/api/wishes"):
            self.send_json({"error": "Không tìm thấy API."}, 404)
            return
        try:
            payload = self.read_json()
        except ValueError as exc:
            status = 413 if "quá lớn" in str(exc) else 400
            self.send_json({"error": str(exc)}, status)
            return

        if path == "/api/guests":
            name = clean_text(payload.get("name"), 40)
            if not name:
                self.send_json({"error": "Vui lòng nhập tên hợp lệ."}, 400)
                return
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO guests(name, name_key, last_seen) VALUES (?, ?, ?)
                       ON CONFLICT(name_key) DO UPDATE SET name=excluded.name, last_seen=excluded.last_seen""",
                    (name, name.casefold(), utc_now()),
                )
            self.send_json({"ok": True}, 201)
            return

        name = clean_text(payload.get("name"), 30)
        message = clean_text(payload.get("message"), 280)
        if len(name) < 2:
            self.send_json({"error": "Tên hiển thị cần ít nhất 2 ký tự."}, 400)
            return
        if len(message) < 3:
            self.send_json({"error": "Lời chúc cần ít nhất 3 ký tự."}, 400)
            return
        if rate_limited(self.client_address[0]):
            self.send_json({"error": "Bạn gửi lời chúc hơi nhanh. Hãy thử lại sau ít phút nhé."}, 429)
            return

        created_at = utc_now()
        with get_db() as conn:
            conn.execute("INSERT INTO wishes(name, message, created_at) VALUES (?, ?, ?)", (name, message, created_at))
            conn.execute("DELETE FROM wishes WHERE id NOT IN (SELECT id FROM wishes ORDER BY id DESC LIMIT 500)")
        self.send_json({"ok": True, "wish": {"name": name, "message": message, "created_at": created_at}}, 201)

    def do_HEAD(self) -> None:  # noqa: N802
        if urlparse(self.path).path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
        else:
            self.send_error(404)


def get_lan_ipv4_addresses() -> list[str]:
    """Find likely LAN IPv4 addresses without making an Internet request."""
    found: list[str] = []
    # A UDP connect selects the default route; no application data is sent.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("192.0.2.1", 80))  # TEST-NET address, never contacted over TCP
            ip = probe.getsockname()[0]
            if ip and not ip.startswith("127."):
                found.append(ip)
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in found:
                found.append(ip)
    except OSError:
        pass
    return found


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), WebsiteHandler)
    print("\n🌸 WEBSITE CHÚC MỪNG NGÀY PHỤ NỮ VIỆT NAM 20/10")
    print(f"Mở trên máy tính: http://127.0.0.1:{PORT}")
    lan_ips = get_lan_ipv4_addresses()
    if lan_ips:
        print("\nMỞ TRÊN ĐIỆN THOẠI (cùng Wi-Fi với máy tính):")
        for ip in lan_ips:
            print(f"  http://{ip}:{PORT}")
    else:
        print("\nKhông tự tìm được IPv4. Trên Windows hãy chạy ipconfig và tìm IPv4 Address.")
    print("Không dùng 127.0.0.1 trên điện thoại — địa chỉ đó trỏ về chính điện thoại.")
    print("Nếu vẫn không kết nối được, chạy allow_phone_wifi.bat bằng quyền Administrator;")
    print("chỉ dùng trên mạng Wi-Fi gia đình đáng tin cậy và đặt Network profile là Private.")
    print("Dữ liệu lưu tại:", DB_PATH)
    print("Nhấn Ctrl+C để dừng máy chủ.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng website.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
