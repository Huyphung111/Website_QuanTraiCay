# -*- coding: utf-8 -*-
"""
Bích Trái Cây - Bảng giá trái cây
=================================
Web xem giá trái cây cho quán "Bích Trái Cây".

- Khách hàng: chỉ XEM danh sách trái cây (tên, giá, ảnh, thời gian cập nhật).
- Admin: bấm "Truy cập", nhập tài khoản + mật khẩu để có quyền
  THÊM / SỬA / XÓA (CRUD) trái cây.

Công nghệ: Flask + SQLite (gọn nhẹ, không cần cài thêm gì ngoài Flask).
Chạy:  python app.py   ->   mở http://127.0.0.1:5000
"""

import glob
import os
import sqlite3
import sys
import unicodedata
import uuid
from datetime import datetime
from functools import wraps
from urllib.parse import quote

# Đảm bảo in được tiếng Việt trên console Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, abort,
)
from werkzeug.utils import secure_filename

# ─────────────────────────────────────────────────────────────
# CẤU HÌNH
# ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "fruits.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB / ảnh

# Tài khoản admin — ĐỔI lại cho an toàn (nên đặt qua biến môi trường khi deploy,
# để mật khẩu KHÔNG bị lộ trong code công khai trên GitHub).
# Có thể có nhiều tài khoản, tất cả đều quyền admin (CRUD).
ADMIN_USERS = {
    os.environ.get("BICH_ADMIN_USER", "admin"): os.environ.get("BICH_ADMIN_PASS", "bich123"),
    "bichtraicay": os.environ.get("BICH_ADMIN_PASS2", "123456"),
}

# Hai trạng thái của trái cây
STATUS_AVAILABLE = "Còn bán"
STATUS_SOLD_OUT = "Hết hàng"

# Khóa bí mật cho session (đăng nhập). Nên đổi khi chạy thật.
SECRET_KEY = os.environ.get("BICH_SECRET_KEY", "doi-chuoi-bi-mat-nay-di-nhe")

# Thông tin quán (hiện ở header + footer)
SHOP_INFO = {
    "name": "Bích Trái Cây",
    "tagline": "Bảng giá hôm nay",
    "address": "157 Nguyễn Hữu Tiến, P. Tây Thạnh, TP.HCM",
    "phone": "0937 724 995",
}
# Link mở Google Maps theo địa chỉ quán (bấm vào để xem vị trí).
SHOP_INFO["maps_url"] = "https://www.google.com/maps/search/?api=1&query=" + quote(SHOP_INFO["address"])


def load_provinces():
    """Đọc 34 tỉnh/thành từ file data/tinh_thanh_viet_nam_34*.md (bảng Markdown)."""
    names = []
    files = sorted(glob.glob(os.path.join(DATA_DIR, "tinh_thanh_viet_nam_34*.md")))
    if files:
        with open(files[0], encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line.startswith("|"):
                    continue
                cells = [c.strip() for c in line.strip("|").split("|")]
                # Dòng dữ liệu có dạng | số | tên tỉnh | ... |
                if len(cells) >= 2 and cells[0].isdigit():
                    names.append(cells[1])
    return names


# Danh sách chọn cho ô "Xuất xứ": Nhập khẩu + 34 tỉnh thành.
ORIGIN_OPTIONS = ["Nhập khẩu"] + load_provinces()

# ─────────────────────────────────────────────────────────────
# KHỞI TẠO FLASK
# ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# CƠ SỞ DỮ LIỆU (SQLite)
# ─────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Tạo bảng và nạp dữ liệu mẫu nếu DB còn trống."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fruits (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            origin     TEXT    DEFAULT '',
            price      INTEGER NOT NULL DEFAULT 0,
            unit       TEXT    DEFAULT 'đ/kg',
            badge      TEXT    DEFAULT 'Còn bán',
            emoji      TEXT    DEFAULT '🍎',
            image      TEXT    DEFAULT '',
            updated_at TEXT    NOT NULL
        )
        """
    )
    # Bảng cài đặt chung (dạng khóa-giá trị) — dùng cho chế độ "Tạm nghỉ"
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) AS c FROM fruits").fetchone()["c"]
    if count == 0:
        now = datetime.now().isoformat(timespec="seconds")
        A, S = STATUS_AVAILABLE, STATUS_SOLD_OUT  # cho gọn
        # (tên, xuất xứ, giá, đơn vị, trạng thái, emoji) — xuất xứ theo 34 tỉnh thành mới
        seed = [
            ("Dưa hấu", "Tây Ninh", 8000, "đ/kg", A, "🍉"),
            ("Chuối già Nam Mỹ", "Đồng Nai", 22000, "đ/kg", A, "🍌"),
            ("Nho xanh Mỹ", "Nhập khẩu", 85000, "đ/kg", A, "🍇"),
            ("Xoài cát Hòa Lộc", "Đồng Tháp", 55000, "đ/kg", A, "🥭"),
            ("Dứa mật", "An Giang", 15000, "đ/trái", A, "🍍"),
            ("Dâu tây Đà Lạt", "Lâm Đồng", 65000, "đ/hộp", A, "🍓"),
            ("Cam sành", "Vĩnh Long", 30000, "đ/kg", A, "🍊"),
            ("Chanh vàng Mỹ", "Nhập khẩu", 120000, "đ/kg", A, "🍋"),
            ("Đào vàng", "Nhập khẩu", 95000, "đ/kg", A, "🍑"),
            ("Dưa lưới Nhật", "Nhập khẩu", 280000, "đ/trái", S, "🍈"),
            ("Cherry đỏ Mỹ", "Nhập khẩu", 199000, "đ/kg", A, "🍒"),
            ("Lê Hàn Quốc", "Nhập khẩu", 145000, "đ/kg", A, "🍐"),
        ]
        conn.executemany(
            """INSERT INTO fruits (name, origin, price, unit, badge, emoji, image, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, '', ?)""",
            [(n, o, p, u, b, e, now) for (n, o, p, u, b, e) in seed],
        )
        conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# TIỆN ÍCH
# ─────────────────────────────────────────────────────────────
def nfc(text):
    """Chuẩn hóa tiếng Việt về dạng NFC để so sánh/lưu trữ nhất quán.

    Tránh lỗi 'Hết hàng' (NFD) không khớp 'Hết hàng' (NFC) khi so sánh chuỗi.
    """
    return unicodedata.normalize("NFC", (text or "").strip())


def allowed_file(filename):
    return "." in filename and \
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def format_price(value):
    """8000 -> '8.000' (dấu chấm ngăn cách hàng nghìn kiểu VN)."""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)


def relative_time(iso_str):
    """Đổi thời gian ISO thành dạng tương đối tiếng Việt:
    'vừa xong', 'X phút trước', 'X giờ trước', 'X ngày trước'."""
    try:
        dt = datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        return ""
    secs = (datetime.now() - dt).total_seconds()
    if secs < 60:
        return "vừa xong"
    if secs < 3600:
        return f"{int(secs // 60)} phút trước"
    if secs < 86400:
        return f"{int(secs // 3600)} giờ trước"
    return f"{int(secs // 86400)} ngày trước"


def format_date_vn(iso_date):
    """'2026-07-20' -> '20/07/2026'."""
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return ""


# ── Cài đặt chung (khóa-giá trị) ──
def get_setting(key, default=""):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()


def get_break():
    """Trạng thái chế độ 'Tạm nghỉ' của quán."""
    until = get_setting("break_until", "")
    return {
        "enabled": get_setting("break_enabled", "0") == "1",
        "until": until,                          # 'YYYY-MM-DD' (cho ô input)
        "until_text": format_date_vn(until),     # 'dd/mm/yyyy' (để hiển thị)
        "message": get_setting("break_message", ""),
    }


def fruit_to_dict(row):
    """Chuyển 1 dòng DB thành dict đã định dạng sẵn cho template/JS."""
    return {
        "id": row["id"],
        "name": row["name"],
        "origin": row["origin"] or "",
        "price": row["price"],
        "price_text": format_price(row["price"]),
        "unit": row["unit"] or "đ/kg",
        "badge": row["badge"] or "",
        "emoji": row["emoji"] or "🍎",
        "image": row["image"] or "",
        "image_url": url_for("static", filename="uploads/" + row["image"]) if row["image"] else "",
        "updated_at": row["updated_at"],
    }


def is_admin():
    return session.get("is_admin", False)


def admin_required(f):
    """Chặn các route CRUD nếu chưa đăng nhập admin."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not is_admin():
            return jsonify({"ok": False, "error": "Bạn cần đăng nhập admin."}), 401
        return f(*args, **kwargs)
    return wrapper


def save_uploaded_image(file_storage):
    """Lưu ảnh tải lên, trả về tên file (đã đổi tên duy nhất). '' nếu không có."""
    if not file_storage or file_storage.filename == "":
        return ""
    if not allowed_file(file_storage.filename):
        raise ValueError("Định dạng ảnh không hợp lệ (chỉ png, jpg, jpeg, gif, webp).")
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(UPLOAD_DIR, secure_filename(fname)))
    return fname


def delete_image_file(filename):
    """Xóa file ảnh trong thư mục uploads (nếu tồn tại)."""
    if not filename:
        return
    path = os.path.join(UPLOAD_DIR, filename)
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────
# ROUTES — TRANG CHÍNH
# ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    conn = get_db()
    rows = conn.execute("SELECT * FROM fruits ORDER BY id DESC").fetchall()
    conn.close()

    fruits = [fruit_to_dict(r) for r in rows]

    # Thời gian cập nhật gần nhất (hiện trên đầu danh sách)
    last_update = ""
    if rows:
        latest = max(r["updated_at"] for r in rows)
        last_update = relative_time(latest)

    return render_template(
        "index.html",
        shop=SHOP_INFO,
        fruits=fruits,
        last_update=last_update,
        is_admin=is_admin(),
        origins=ORIGIN_OPTIONS,
        status_sold_out=STATUS_SOLD_OUT,
        brk=get_break(),
        today=datetime.now().date().isoformat(),
    )


# ─────────────────────────────────────────────────────────────
# ROUTES — ĐĂNG NHẬP / ĐĂNG XUẤT ADMIN
# ─────────────────────────────────────────────────────────────
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if username in ADMIN_USERS and ADMIN_USERS[username] == password:
        session["is_admin"] = True
        session["admin_user"] = username
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Sai tài khoản hoặc mật khẩu."}), 401


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("is_admin", None)
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────
# ROUTES — CRUD TRÁI CÂY (chỉ admin)
# ─────────────────────────────────────────────────────────────
@app.route("/fruits/add", methods=["POST"])
@admin_required
def add_fruit():
    form = request.form
    name = nfc(form.get("name"))
    if not name:
        return jsonify({"ok": False, "error": "Vui lòng nhập tên trái cây."}), 400

    try:
        price = int(float(form.get("price") or 0))
    except ValueError:
        return jsonify({"ok": False, "error": "Giá phải là số."}), 400

    origin = nfc(form.get("origin"))
    unit = nfc(form.get("unit")) or "đ/kg"
    badge = nfc(form.get("badge")) or STATUS_AVAILABLE
    if badge not in (STATUS_AVAILABLE, STATUS_SOLD_OUT):
        badge = STATUS_AVAILABLE
    emoji = (form.get("emoji") or "🍎").strip() or "🍎"

    try:
        image = save_uploaded_image(request.files.get("image"))
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    now = datetime.now().isoformat(timespec="seconds")
    conn = get_db()
    conn.execute(
        """INSERT INTO fruits (name, origin, price, unit, badge, emoji, image, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, origin, price, unit, badge, emoji, image, now),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/fruits/<int:fruit_id>/edit", methods=["POST"])
@admin_required
def edit_fruit(fruit_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM fruits WHERE id = ?", (fruit_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy trái cây."}), 404

    form = request.form
    name = nfc(form.get("name"))
    if not name:
        conn.close()
        return jsonify({"ok": False, "error": "Vui lòng nhập tên trái cây."}), 400

    try:
        price = int(float(form.get("price") or 0))
    except ValueError:
        conn.close()
        return jsonify({"ok": False, "error": "Giá phải là số."}), 400

    origin = nfc(form.get("origin"))
    unit = nfc(form.get("unit")) or "đ/kg"
    badge = nfc(form.get("badge")) or STATUS_AVAILABLE
    if badge not in (STATUS_AVAILABLE, STATUS_SOLD_OUT):
        badge = STATUS_AVAILABLE

    # Ảnh: nếu tải ảnh mới thì thay, xóa ảnh cũ. Nếu không thì giữ nguyên.
    image = row["image"]
    new_file = request.files.get("image")
    if new_file and new_file.filename:
        try:
            new_image = save_uploaded_image(new_file)
        except ValueError as e:
            conn.close()
            return jsonify({"ok": False, "error": str(e)}), 400
        delete_image_file(row["image"])
        image = new_image

    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """UPDATE fruits
           SET name=?, origin=?, price=?, unit=?, badge=?, image=?, updated_at=?
           WHERE id=?""",
        (name, origin, price, unit, badge, image, now, fruit_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/fruits/<int:fruit_id>/delete", methods=["POST"])
@admin_required
def delete_fruit(fruit_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM fruits WHERE id = ?", (fruit_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy trái cây."}), 404
    conn.execute("DELETE FROM fruits WHERE id = ?", (fruit_id,))
    conn.commit()
    conn.close()
    delete_image_file(row["image"])
    return jsonify({"ok": True})


# ─────────────────────────────────────────────────────────────
# ROUTES — CHẾ ĐỘ TẠM NGHỈ (chỉ admin)
# ─────────────────────────────────────────────────────────────
@app.route("/break/save", methods=["POST"])
@admin_required
def break_save():
    data = request.get_json(silent=True) or request.form
    until = (data.get("until") or "").strip()
    message = nfc(data.get("message"))

    try:
        chosen = datetime.strptime(until, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "error": "Vui lòng chọn ngày hợp lệ."}), 400

    if chosen < datetime.now().date():
        return jsonify({"ok": False, "error": "Ngày nghỉ tới phải từ hôm nay trở đi."}), 400

    set_setting("break_enabled", "1")
    set_setting("break_until", until)
    set_setting("break_message", message)
    return jsonify({"ok": True})


@app.route("/break/off", methods=["POST"])
@admin_required
def break_off():
    set_setting("break_enabled", "0")
    return jsonify({"ok": True})


# Tạo bảng + nạp dữ liệu mẫu ngay khi import.
# Phải đặt ở cấp module (không phải trong __main__) để khi deploy bằng WSGI
# (PythonAnywhere, gunicorn...) database vẫn được khởi tạo đầy đủ.
init_db()


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Bich Trai Cay dang chay tai:  http://127.0.0.1:5000")
    print("Bam Ctrl+C de dung server.")
    app.run(debug=True, host="0.0.0.0", port=5000)
