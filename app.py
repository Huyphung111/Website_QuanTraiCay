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
import json
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
    # Các bảng quản lý hóa đơn (chỉ dùng trong khu quản trị).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoice_shops (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL UNIQUE,
            address TEXT DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_id    INTEGER NOT NULL,
            code       TEXT    NOT NULL,
            date       TEXT    NOT NULL,
            note       TEXT    DEFAULT '',
            photo      TEXT    DEFAULT '',
            created_at TEXT    NOT NULL,
            UNIQUE(shop_id, code),
            FOREIGN KEY(shop_id) REFERENCES invoice_shops(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoice_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            fruit      TEXT    NOT NULL,
            price      REAL    NOT NULL DEFAULT 0,
            kg         REAL    NOT NULL DEFAULT 0,
            FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS invoice_photos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            filename      TEXT    NOT NULL,
            original_name TEXT    DEFAULT '',
            source        TEXT    DEFAULT 'archive',
            invoice_id    INTEGER,
            file_size     INTEGER DEFAULT 0,
            created_at    TEXT    NOT NULL
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

    shop_count = conn.execute("SELECT COUNT(*) AS c FROM invoice_shops").fetchone()["c"]
    if shop_count == 0:
        conn.executemany(
            "INSERT INTO invoice_shops (name, address) VALUES (?, ?)",
            [
                ("Quán 1", "157 Nguyễn Hữu Tiến"),
                ("Quán 2", "Chi nhánh 2"),
                ("Quán 3", "Chi nhánh 3"),
            ],
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


def invoice_shop_to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "address": row["address"] or "Chưa cập nhật",
        "invoice_count": row["invoice_count"] if "invoice_count" in row.keys() else 0,
    }


def invoice_to_dict(row, items=None):
    data = {
        "id": row["id"],
        "shop_id": row["shop_id"],
        "code": row["code"],
        "date": row["date"],
        "note": row["note"] or "",
        "photo": row["photo"] or "",
        "photo_url": url_for("static", filename="uploads/" + row["photo"]) if row["photo"] else "",
        "created_at": row["created_at"],
        "items": items or [],
    }
    data["total"] = sum(float(i["price"]) * float(i["kg"]) for i in data["items"])
    return data


def invoice_photo_to_dict(row):
    return {
        "id": row["id"],
        "filename": row["filename"],
        "original_name": row["original_name"] or row["filename"],
        "source": row["source"] or "archive",
        "invoice_id": row["invoice_id"],
        "file_size": row["file_size"] or 0,
        "created_at": row["created_at"],
        "url": url_for("static", filename="uploads/" + row["filename"]),
    }


def next_invoice_code(conn, shop_id):
    rows = conn.execute("SELECT code FROM invoices WHERE shop_id = ?", (shop_id,)).fetchall()
    max_num = 0
    for row in rows:
        code = row["code"] or ""
        if code.startswith("HD") and code[2:].isdigit():
            max_num = max(max_num, int(code[2:]))
    return "HD" + str(max_num + 1).zfill(3)


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


def remember_invoice_photo(conn, filename, original_name="", source="archive", invoice_id=None):
    if not filename:
        return
    path = os.path.join(UPLOAD_DIR, filename)
    file_size = os.path.getsize(path) if os.path.isfile(path) else 0

    # Lấy extension của file
    ext = ""
    orig_name_to_use = original_name or filename
    if "." in orig_name_to_use:
        ext = "." + orig_name_to_use.rsplit(".", 1)[1].lower()

    # Sinh tên tự động theo định dạng ngay[D]thang[M]nam[Y]ban[STT].[ext]
    now = datetime.now()
    date_str = f"ngay{now.day}thang{now.month}nam{now.year}"
    today_prefix = now.strftime("%Y-%m-%d")

    # Đếm số lượng ảnh được tải lên trong ngày hôm nay để lấy số thứ tự
    count_row = conn.execute(
        "SELECT COUNT(*) as cnt FROM invoice_photos WHERE created_at LIKE ?",
        (today_prefix + "%",)
    ).fetchone()
    seq = (count_row["cnt"] if count_row else 0) + 1

    auto_name = f"{date_str}ban{seq}{ext}"

    conn.execute(
        """INSERT INTO invoice_photos
           (filename, original_name, source, invoice_id, file_size, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            filename,
            auto_name,
            source,
            invoice_id,
            file_size,
            now.isoformat(timespec="seconds"),
        ),
    )


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


# ─────────────────────────────────────────────────────────────
# ROUTES — QUẢN LÝ HÓA ĐƠN (chỉ admin)
# ─────────────────────────────────────────────────────────────
@app.route("/invoices")
def invoices_page():
    if not is_admin():
        return redirect(url_for("index"))
    return render_template("invoices.html", shop=SHOP_INFO)


@app.route("/api/invoice-shops", methods=["GET"])
@admin_required
def api_invoice_shops():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT s.id, s.name, s.address, COUNT(i.id) AS invoice_count
        FROM invoice_shops s
        LEFT JOIN invoices i ON i.shop_id = s.id
        GROUP BY s.id
        ORDER BY s.id
        """
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "shops": [invoice_shop_to_dict(r) for r in rows]})


@app.route("/api/invoice-shops", methods=["POST"])
@admin_required
def api_add_invoice_shop():
    data = request.get_json(silent=True) or request.form
    name = nfc(data.get("name"))
    address = nfc(data.get("address")) or "Chưa cập nhật"
    if not name:
        return jsonify({"ok": False, "error": "Vui lòng nhập tên quán."}), 400
    if len(name) > 30:
        return jsonify({"ok": False, "error": "Tên quán tối đa 30 ký tự."}), 400

    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO invoice_shops (name, address) VALUES (?, ?)",
            (name, address),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"ok": False, "error": "Tên quán này đã tồn tại."}), 400

    row = conn.execute(
        "SELECT id, name, address, 0 AS invoice_count FROM invoice_shops WHERE id = ?",
        (cur.lastrowid,),
    ).fetchone()
    conn.close()
    return jsonify({"ok": True, "shop": invoice_shop_to_dict(row)})


@app.route("/api/invoice-shops/<int:shop_id>/edit", methods=["POST"])
@admin_required
def api_edit_invoice_shop(shop_id):
    data = request.get_json(silent=True) or request.form
    name = nfc(data.get("name"))
    address = nfc(data.get("address")) or "Chưa cập nhật"
    if not name:
        return jsonify({"ok": False, "error": "Vui lòng nhập tên quán."}), 400
    if len(name) > 30:
        return jsonify({"ok": False, "error": "Tên quán tối đa 30 ký tự."}), 400

    conn = get_db()
    row = conn.execute("SELECT * FROM invoice_shops WHERE id = ?", (shop_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy quán."}), 404
    try:
        conn.execute(
            "UPDATE invoice_shops SET name = ?, address = ? WHERE id = ?",
            (name, address, shop_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"ok": False, "error": "Tên quán này đã tồn tại."}), 400

    updated = conn.execute(
        """
        SELECT s.id, s.name, s.address, COUNT(i.id) AS invoice_count
        FROM invoice_shops s
        LEFT JOIN invoices i ON i.shop_id = s.id
        WHERE s.id = ?
        GROUP BY s.id
        """,
        (shop_id,),
    ).fetchone()
    conn.close()
    return jsonify({"ok": True, "shop": invoice_shop_to_dict(updated)})


@app.route("/api/invoice-shops/<int:shop_id>/delete", methods=["POST"])
@admin_required
def api_delete_invoice_shop(shop_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM invoice_shops WHERE id = ?", (shop_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy quán."}), 404

    invoice_rows = conn.execute("SELECT id FROM invoices WHERE shop_id = ?", (shop_id,)).fetchall()
    invoice_ids = [r["id"] for r in invoice_rows]
    if invoice_ids:
        placeholders = ",".join("?" for _ in invoice_ids)
        conn.execute(f"UPDATE invoice_photos SET invoice_id = NULL WHERE invoice_id IN ({placeholders})", invoice_ids)
        conn.execute(f"DELETE FROM invoice_items WHERE invoice_id IN ({placeholders})", invoice_ids)
    conn.execute("DELETE FROM invoices WHERE shop_id = ?", (shop_id,))
    conn.execute("DELETE FROM invoice_shops WHERE id = ?", (shop_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/invoice-shops/<int:shop_id>/invoices", methods=["GET"])
@admin_required
def api_invoices(shop_id):
    date_filter = (request.args.get("date") or "").strip()
    conn = get_db()
    shop = conn.execute("SELECT * FROM invoice_shops WHERE id = ?", (shop_id,)).fetchone()
    if not shop:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy quán."}), 404

    params = [shop_id]
    where_date = ""
    if date_filter:
        where_date = " AND date = ?"
        params.append(date_filter)

    rows = conn.execute(
        f"SELECT * FROM invoices WHERE shop_id = ?{where_date} ORDER BY date DESC, id DESC",
        params,
    ).fetchall()
    invoice_ids = [r["id"] for r in rows]
    items_by_invoice = {invoice_id: [] for invoice_id in invoice_ids}
    if invoice_ids:
        placeholders = ",".join("?" for _ in invoice_ids)
        item_rows = conn.execute(
            f"""SELECT id, invoice_id, fruit, price, kg
                FROM invoice_items
                WHERE invoice_id IN ({placeholders})
                ORDER BY id""",
            invoice_ids,
        ).fetchall()
        for item in item_rows:
            items_by_invoice[item["invoice_id"]].append(
                {
                    "id": item["id"],
                    "fruit": item["fruit"],
                    "price": item["price"],
                    "kg": item["kg"],
                }
            )
    conn.close()

    invoices = [invoice_to_dict(r, items_by_invoice.get(r["id"], [])) for r in rows]
    return jsonify({
        "ok": True,
        "shop": {"id": shop["id"], "name": shop["name"], "address": shop["address"] or ""},
        "invoices": invoices,
        "total": sum(inv["total"] for inv in invoices),
    })


@app.route("/api/invoice-shops/<int:shop_id>/invoices", methods=["POST"])
@admin_required
def api_add_invoice(shop_id):
    conn = get_db()
    shop = conn.execute("SELECT * FROM invoice_shops WHERE id = ?", (shop_id,)).fetchone()
    if not shop:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy quán."}), 404

    date = (request.form.get("date") or "").strip()
    note = nfc(request.form.get("note"))
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        conn.close()
        return jsonify({"ok": False, "error": "Vui lòng chọn ngày hợp lệ."}), 400

    try:
        raw_items = json.loads(request.form.get("items") or "[]")
    except json.JSONDecodeError:
        conn.close()
        return jsonify({"ok": False, "error": "Danh sách hàng không hợp lệ."}), 400

    items = []
    for item in raw_items:
        fruit = nfc(item.get("fruit"))
        try:
            price = float(item.get("price"))
            kg = float(item.get("kg"))
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"ok": False, "error": "Giá và kg phải là số."}), 400
        if not fruit or price < 0 or kg <= 0:
            conn.close()
            return jsonify({"ok": False, "error": "Vui lòng điền đủ thông tin hàng hóa."}), 400
        items.append({"fruit": fruit, "price": price, "kg": kg})

    if not items:
        conn.close()
        return jsonify({"ok": False, "error": "Vui lòng thêm ít nhất một mặt hàng."}), 400

    try:
        photo = save_uploaded_image(request.files.get("photo"))
    except ValueError as e:
        conn.close()
        return jsonify({"ok": False, "error": str(e)}), 400

    now = datetime.now().isoformat(timespec="seconds")
    code = next_invoice_code(conn, shop_id)
    cur = conn.execute(
        """INSERT INTO invoices (shop_id, code, date, note, photo, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (shop_id, code, date, note, photo, now),
    )
    invoice_id = cur.lastrowid
    conn.executemany(
        """INSERT INTO invoice_items (invoice_id, fruit, price, kg)
           VALUES (?, ?, ?, ?)""",
        [(invoice_id, i["fruit"], i["price"], i["kg"]) for i in items],
    )
    remember_invoice_photo(
        conn,
        photo,
        request.files.get("photo").filename if request.files.get("photo") else "",
        "invoice",
        invoice_id,
    )
    conn.commit()
    row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()
    return jsonify({"ok": True, "invoice": invoice_to_dict(row, items)})


@app.route("/api/invoice-shops/<int:shop_id>/invoices/<int:invoice_id>/edit", methods=["POST"])
@admin_required
def api_edit_invoice(shop_id, invoice_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM invoices WHERE id = ? AND shop_id = ?",
        (invoice_id, shop_id),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy hóa đơn."}), 404

    date = (request.form.get("date") or "").strip()
    note = nfc(request.form.get("note"))
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        conn.close()
        return jsonify({"ok": False, "error": "Vui lòng chọn ngày hợp lệ."}), 400

    try:
        raw_items = json.loads(request.form.get("items") or "[]")
    except json.JSONDecodeError:
        conn.close()
        return jsonify({"ok": False, "error": "Danh sách hàng không hợp lệ."}), 400

    items = []
    for item in raw_items:
        fruit = nfc(item.get("fruit"))
        try:
            price = float(item.get("price"))
            kg = float(item.get("kg"))
        except (TypeError, ValueError):
            conn.close()
            return jsonify({"ok": False, "error": "Giá và kg phải là số."}), 400
        if not fruit or price < 0 or kg <= 0:
            conn.close()
            return jsonify({"ok": False, "error": "Vui lòng điền đủ thông tin hàng hóa."}), 400
        items.append({"fruit": fruit, "price": price, "kg": kg})

    if not items:
        conn.close()
        return jsonify({"ok": False, "error": "Vui lòng thêm ít nhất một mặt hàng."}), 400

    clear_photo = request.form.get("clear_photo") == "1"
    old_photo = row["photo"] or ""
    photo = old_photo

    new_file = request.files.get("photo")
    if clear_photo:
        photo = ""
    elif new_file and new_file.filename:
        try:
            photo = save_uploaded_image(new_file)
        except ValueError as e:
            conn.close()
            return jsonify({"ok": False, "error": str(e)}), 400

    if old_photo and photo != old_photo:
        conn.execute("DELETE FROM invoice_photos WHERE filename = ?", (old_photo,))
        delete_image_file(old_photo)

    conn.execute(
        "UPDATE invoices SET date = ?, note = ?, photo = ? WHERE id = ?",
        (date, note, photo, invoice_id),
    )
    conn.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    conn.executemany(
        """INSERT INTO invoice_items (invoice_id, fruit, price, kg)
           VALUES (?, ?, ?, ?)""",
        [(invoice_id, i["fruit"], i["price"], i["kg"]) for i in items],
    )
    if new_file and new_file.filename:
        remember_invoice_photo(conn, photo, new_file.filename, "invoice", invoice_id)
    conn.commit()
    updated = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()
    return jsonify({"ok": True, "invoice": invoice_to_dict(updated, items)})


@app.route("/api/invoice-shops/<int:shop_id>/invoices/<int:invoice_id>", methods=["GET"])
@admin_required
def api_invoice_detail(shop_id, invoice_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM invoices WHERE id = ? AND shop_id = ?",
        (invoice_id, shop_id),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy hóa đơn."}), 404
    item_rows = conn.execute(
        "SELECT id, fruit, price, kg FROM invoice_items WHERE invoice_id = ? ORDER BY id",
        (invoice_id,),
    ).fetchall()
    conn.close()
    items = [{"id": r["id"], "fruit": r["fruit"], "price": r["price"], "kg": r["kg"]} for r in item_rows]
    return jsonify({"ok": True, "invoice": invoice_to_dict(row, items)})


@app.route("/api/invoice-shops/<int:shop_id>/invoices/<int:invoice_id>/delete", methods=["POST"])
@admin_required
def api_delete_invoice(shop_id, invoice_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM invoices WHERE id = ? AND shop_id = ?",
        (invoice_id, shop_id),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy hóa đơn."}), 404
    conn.execute("UPDATE invoice_photos SET invoice_id = NULL WHERE invoice_id = ?", (invoice_id,))
    conn.execute("DELETE FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/invoice-photos", methods=["GET"])
@admin_required
def api_invoice_photos():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM invoice_photos ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "photos": [invoice_photo_to_dict(r) for r in rows]})


@app.route("/api/invoice-photos/upload", methods=["POST"])
@admin_required
def api_upload_invoice_photos():
    files = request.files.getlist("photos")
    if not files:
        return jsonify({"ok": False, "error": "Vui lòng chọn ít nhất một ảnh."}), 400

    saved = []
    conn = get_db()
    try:
        for file_storage in files:
            if not file_storage or not file_storage.filename:
                continue
            filename = save_uploaded_image(file_storage)
            remember_invoice_photo(conn, filename, file_storage.filename, "archive", None)
            saved.append(filename)
    except ValueError as e:
        conn.close()
        return jsonify({"ok": False, "error": str(e)}), 400

    if not saved:
        conn.close()
        return jsonify({"ok": False, "error": "Không có ảnh hợp lệ để lưu."}), 400

    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": f"Đã lưu {len(saved)} ảnh vào kho."})


@app.route("/api/invoice-photos/<int:photo_id>/delete", methods=["POST"])
@admin_required
def api_delete_invoice_photo(photo_id):
    conn = get_db()
    row = conn.execute(
        "SELECT filename FROM invoice_photos WHERE id = ?", (photo_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy ảnh."}), 404
    filename = row["filename"]
    conn.execute("UPDATE invoices SET photo = '' WHERE photo = ?", (filename,))
    conn.execute("DELETE FROM invoice_photos WHERE id = ?", (photo_id,))
    conn.commit()
    conn.close()
    delete_image_file(filename)
    return jsonify({"ok": True})


@app.route("/api/invoice-photos/<int:photo_id>/edit-name", methods=["POST"])
@admin_required
def api_edit_invoice_photo_name(photo_id):
    data = request.get_json(silent=True) or request.form
    name = nfc(data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "Vui lòng nhập tên ảnh."}), 400
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM invoice_photos WHERE id = ?", (photo_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Không tìm thấy ảnh."}), 404
    conn.execute(
        "UPDATE invoice_photos SET original_name = ? WHERE id = ?",
        (name, photo_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})



@app.route('/api/invoice-shops/<int:shop_id>/export-pdf', methods=['GET'])
@admin_required
def api_export_pdf(shop_id):
    from io import BytesIO
    from flask import Response as FlaskResponse
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        return jsonify({'ok': False, 'error': 'Chua cai reportlab. Chay: pip install reportlab'}), 500

    font_name = 'Helvetica'
    bold_fn = 'Helvetica-Bold'
    font_dir = os.path.join(BASE_DIR, 'static', 'fonts')
    try:
        fp = os.path.join(font_dir, 'vifont.ttf')
        fbp = os.path.join(font_dir, 'vifont-bold.ttf')
        if os.path.exists(fp) and os.path.exists(fbp):
            pdfmetrics.registerFont(TTFont('ViFont', fp))
            pdfmetrics.registerFont(TTFont('ViFont-Bold', fbp))
            font_name = 'ViFont'
            bold_fn = 'ViFont-Bold'
    except Exception:
        pass

    date_filter = (request.args.get('date') or '').strip()
    conn = get_db()
    shop = conn.execute('SELECT * FROM invoice_shops WHERE id = ?', (shop_id,)).fetchone()
    if not shop:
        conn.close()
        return jsonify({'ok': False, 'error': 'Khong tim thay quan.'}), 404

    params = [shop_id]
    where_date = ''
    if date_filter:
        where_date = ' AND date = ?'
        params.append(date_filter)
    rows = conn.execute(
        'SELECT * FROM invoices WHERE shop_id = ?' + where_date + ' ORDER BY date DESC, id DESC',
        params,
    ).fetchall()
    invoice_ids = [r['id'] for r in rows]
    items_by_invoice = {iid: [] for iid in invoice_ids}
    if invoice_ids:
        ph = ','.join('?' for _ in invoice_ids)
        item_rows = conn.execute(
            'SELECT invoice_id, fruit, price, kg FROM invoice_items WHERE invoice_id IN (' + ph + ') ORDER BY id',
            invoice_ids,
        ).fetchall()
        for item in item_rows:
            items_by_invoice[item['invoice_id']].append(item)
    conn.close()

    invoices = [invoice_to_dict(r, items_by_invoice.get(r['id'], [])) for r in rows]
    total_all = sum(inv['total'] for inv in invoices)

    def fmt_money(n):
        return '{:,} đ'.format(int(round(n))).replace(',', '.')
    def fmt_date(d):
        try:
            p2 = d.split('-')
            return p2[2] + '/' + p2[1] + '/' + p2[0]
        except Exception:
            return d or ''

    buf = BytesIO()
    col_w = [10*mm, 18*mm, 22*mm, 35*mm, 57*mm, 30*mm]
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=20*mm)

    C_GOLD = colors.HexColor('#E8A020')
    C_LIGHT = colors.HexColor('#FFF3DC')
    C_BORDER = colors.HexColor('#E0D8CC')
    C_DARK = colors.HexColor('#C8841A')
    C_GREEN = colors.HexColor('#2E7D32')
    C_ZEBRA = colors.HexColor('#FAFAF8')

    def p(text, fn=None, size=9, color=None, align=0):
        fn = fn or font_name
        st = ParagraphStyle('x', fontName=fn, fontSize=size, leading=size+3, alignment=align, textColor=color or colors.black)
        return Paragraph(text, st)

    story = []
    tw = sum(col_w)
    shop_name_v = shop['name'] or 'Cửa hàng'
    shop_addr_v = shop['address'] or 'Chưa cập nhật'
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    period_str = ('Ngày: ' + fmt_date(date_filter)) if date_filter else 'Tất cả hóa đơn'

    hdr = Table([
        [p('BÍCH TRÁI CÂY', fn=bold_fn, size=16, color=C_GOLD), p(shop_name_v, fn=bold_fn, size=12, align=2)],
        [p('Hệ thống quản lý cửa hàng trái cây sạch', size=9, color=colors.HexColor('#666666')), p('Ngày lập: ' + now_str, size=9, color=colors.HexColor('#888888'), align=2)],
        [p('Địa chỉ: ' + shop_addr_v, size=9, color=colors.HexColor('#666666')), p('', size=9)],
    ], colWidths=[tw*0.6, tw*0.4])
    hdr.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),3),('LINEBELOW',(0,2),(-1,2),1.5,C_GOLD)]))
    story.append(hdr)
    story.append(Spacer(1, 6*mm))
    story.append(p('BÁO CÁO DOANH THU & DANH SÁCH HÓA ĐƠN', fn=bold_fn, size=14, align=1))
    story.append(Spacer(1, 2*mm))
    story.append(p(period_str, size=10, color=colors.HexColor('#666666'), align=1))
    story.append(Spacer(1, 6*mm))

    tdata = [[p('STT', fn=bold_fn, align=1), p('Mã HD', fn=bold_fn, align=1), p('Ngày tạo', fn=bold_fn, align=1), p('Ghi chú', fn=bold_fn), p('Mặt hàng', fn=bold_fn), p('Thành tiền', fn=bold_fn, align=2)]]
    for idx, inv in enumerate(invoices):
        fruits = ', '.join(item['fruit'] for item in (inv['items'] or [])) or '-'
        tdata.append([p(str(idx+1), align=1), p(inv['code'], fn=bold_fn, align=1), p(fmt_date(inv['date']), align=1), p(inv['note'] or '-'), p(fruits), p(fmt_money(inv['total']), fn=bold_fn, align=2, color=C_GREEN)])
    tbl = Table(tdata, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),C_LIGHT),('TEXTCOLOR',(0,0),(-1,0),C_DARK),('GRID',(0,0),(-1,-1),0.5,C_BORDER),('LINEABOVE',(0,0),(-1,0),1.5,C_GOLD),('FONTNAME',(0,0),(-1,0),bold_fn),('FONTSIZE',(0,0),(-1,0),9),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,C_ZEBRA]),('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(tbl)
    story.append(Spacer(1, 5*mm))

    tt = Table([[p('TỔNG DOANH THU:', fn=bold_fn, size=11, color=C_DARK, align=2), p(fmt_money(total_all), fn=bold_fn, size=13, color=C_DARK, align=2)]], colWidths=[tw*0.6, tw*0.4])
    tt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),C_LIGHT),('BOX',(0,0),(-1,-1),1.5,C_GOLD),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10)]))
    story.append(tt)
    story.append(Spacer(1, 15*mm))

    st2 = Table([[p('Người lập biểu', fn=bold_fn, size=10, align=1), p(''), p('Đại diện cửa hàng', fn=bold_fn, size=10, align=1)]], colWidths=[tw*0.35, tw*0.3, tw*0.35])
    st2.setStyle(TableStyle([('BOTTOMPADDING',(0,0),(-1,-1),45),('TOPPADDING',(0,0),(-1,-1),4)]))
    story.append(st2)

    doc.build(story)
    buf.seek(0)
    shop_safe = (shop['name'] or 'quan').replace(' ', '_')
    date_safe = ('_' + date_filter) if date_filter else ''
    fname = 'Danh_sach_hoa_don_' + shop_safe + date_safe + '.pdf'
    return FlaskResponse(buf.read(), mimetype='application/pdf', headers={'Content-Disposition': 'attachment; filename=' + fname})


@app.route("/api/invoice-photos/download-all", methods=["GET"])
@admin_required
def api_download_all_photos():
    """Tải toàn bộ ảnh trong kho dưới dạng file zip, đổi tên tương ứng với original_name."""
    import zipfile
    from io import BytesIO
    from flask import send_file

    conn = get_db()
    rows = conn.execute("SELECT filename, original_name FROM invoice_photos").fetchall()
    conn.close()

    if not rows:
        return jsonify({"ok": False, "error": "Không có ảnh nào để tải."}), 400

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for row in rows:
            filename = row["filename"]
            original_name = row["original_name"]
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            if os.path.isfile(file_path):
                # Đổi tên file trong file zip tương ứng với original_name
                arcname = original_name or filename
                if "." not in arcname and "." in filename:
                    ext = filename.rsplit(".", 1)[1].lower()
                    arcname = f"{arcname}.{ext}"
                zip_file.write(file_path, arcname)
                
    memory_file.seek(0)
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"Kho_anh_Bich_Trai_Cay_{now_str}.zip"
    
    response = send_file(memory_file, mimetype="application/zip")
    response.headers["Content-Disposition"] = f"attachment; filename={zip_name}"
    return response


# Tạo bảng + nạp dữ liệu mẫu ngay khi import.
# Phải đặt ở cấp module (không phải trong __main__) để khi deploy bằng WSGI
# (PythonAnywhere, gunicorn...) database vẫn được khởi tạo đầy đủ.
init_db()


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Bich Trai Cay dang chay tai:  http://127.0.0.1:5000")
    print("Bam Ctrl+C de dung server.")
    app.run(debug=True, host="0.0.0.0", port=5000)
