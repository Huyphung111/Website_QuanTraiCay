# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Flask + SQLite web app for the fruit shop *Bích Trái Cây*. It is **not** a store — no cart, no checkout.
It includes two main features:
1. A public fruit price list ("bảng giá"). Guests read the list; an authenticated admin does CRUD on fruits and toggles a "closed for break" mode.
2. An admin-only Invoice Management system ("Quản lý hóa đơn") to track sales invoices across multiple shop branches.

The entire codebase — comments, UI strings, seed data, even most identifiers' surrounding prose — is in **Vietnamese**. Keep new code and user-facing text in Vietnamese to match.

## Commands

```bash
pip install -r requirements.txt   # only dependency is Flask>=3.0
python app.py                     # runs dev server on http://127.0.0.1:5000 (debug=True)
```

On Windows, double-clicking `run.bat` auto-installs Flask then runs `app.py`.

There is **no build step, no test suite, and no linter**. Changes are verified by running the server and exercising the UI.

## Configuration via environment variables

Secrets are read from env vars with insecure defaults baked in for local use. Override these in production:
- `BICH_ADMIN_USER` / `BICH_ADMIN_PASS` — first admin account (default `admin` / `bich123`)
- `BICH_ADMIN_PASS2` — password for the hardcoded second account `bichtraicay` (default `123456`)
- `BICH_SECRET_KEY` — Flask session signing key

The two accounts live in the `ADMIN_USERS` dict in [app.py](app.py). Passwords are compared in plaintext — there is no hashing.

## Architecture

Everything server-side is in **[app.py](app.py)** (~1000 lines): config, DB layer, utility functions, and all routes (including APIs for invoices). There are no blueprints or modules to chase.

**Two-role model.** Anyone can `GET /`. Admin actions require a session flag set by `POST /login`. The `@admin_required` decorator (returns JSON 401 or redirects to `/`) guards every admin route. `is_admin()` reads `session["is_admin"]` and is passed into the template to switch the UI between guest and admin views.

**Fruit CRUD is fetch + full reload.** Fruit mutations (`/fruits/add`, `/fruits/<id>/edit`, `/fruits/<id>/delete`, `/break/save`, `/break/off`) are `POST` endpoints returning JSON. [static/app.js](static/app.js) submits forms via `fetch`, then calls `window.location.reload()` on success.

**Invoice Management (SPA).** The Invoice page (`/invoices`, rendering [templates/invoices.html](templates/invoices.html)) is an admin-only SPA. It uses [static/invoices.js](static/invoices.js) and [static/invoices.css](static/invoices.css) to interact with backend JSON APIs, performing dynamic DOM updates for CRUD operations on invoice shops, invoices, items, and photos without reloading the page.

**Server→client data handoff.** [templates/index.html](templates/index.html) injects `window.FRUITS = {{ fruits | tojson }}` and `window.BREAK = {{ brk | tojson }}` for pre-filling modals. Fruit search is purely client-side: each card carries a `data-search` attribute (`name + origin`, lowercased) filtered by `runSearch()`.

**SQLite, six tables**, file at `data/fruits.db` (gitignored, auto-created):
- `fruits` — the price-list rows. Seeded with 12 sample fruits on first run if empty.
- `settings` — a generic key/value table. Used for the "Tạm nghỉ" feature via keys `break_enabled`, `break_until`, `break_message`.
- `invoice_shops` — stores the shop branches. Seeded with 3 sample shops on first run if empty.
- `invoices` — stores metadata for invoices (shop ID, code like `HD001`, date, note, photo name).
- `invoice_items` — stores individual items in an invoice (fruit name, price, kg).
- `invoice_photos` — records uploaded photos, linking them to an invoice ID or labeling them as part of the general "archive".

`init_db()` is called **at module top level**, not inside `if __name__ == "__main__"`. This is deliberate so WSGI deployment (PythonAnywhere/gunicorn, which import `app` and never run `__main__`) still initializes the DB. Don't move it.

**Provinces / origin dropdown.** At startup `load_provinces()` parses the Markdown table in `data/tinh_thanh_viet_nam_34*.md` (Vietnam's 34 post-2025-merger provinces) into `ORIGIN_OPTIONS`, prefixed with `"Nhập khẩu"` (imported). The origin `<select>` is populated from this list. If that file is missing or renamed, the dropdown only offers "Nhập khẩu".

**Vietnamese NFC normalization.** All text input passes through `nfc()` (Unicode NFC). This matters: the two status strings `"Còn bán"` / `"Hết hàng"` (constants `STATUS_AVAILABLE` / `STATUS_SOLD_OUT`) drive the sold-out styling, and NFD-vs-NFC mismatches would silently break the equality check. Use these constants rather than literal strings when comparing status.

**Image uploads.** `save_uploaded_image()` validates the extension (`png/jpg/jpeg/gif/webp`, 8MB cap via `MAX_CONTENT_LENGTH`), renames to a `uuid4().hex` filename, and stores under `static/uploads/` (gitignored except `.gitkeep`). Editing a fruit or invoice with a new image saves the new file; deleting a fruit deletes its associated image. Invoices also use this upload system, tracking photos in `invoice_photos` and supporting a multi-file photo archive.

## Deployment

`wsgi_pythonanywhere.py` is a **template**, not a runnable file — it documents the WSGI entry point (`from app import app as application`) and where to set the env-var secrets on the server. See `HUONG_DAN_PYTHONANYWHERE.md` for the full PythonAnywhere walkthrough.

## Runtime data is not tracked

`data/fruits.db` and `static/uploads/*` are gitignored. To reset the DB (and its seeds), delete `data/fruits.db` and restart the server. The design reference `bich-trai-cay.html`, static prototype `quan_ly_hoa_don-1.html`, and its logic specification `LOGIC_PROMPT_quan_ly_hoa_don.md` at the repo root are kept for reference only and are not served.
