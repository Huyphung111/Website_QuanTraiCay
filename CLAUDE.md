# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-page Flask + SQLite web app showing a fruit price list ("bảng giá") for the shop *Bích Trái Cây*. It is **not** a store — no cart, no checkout. Guests read the list; an authenticated admin does CRUD on fruits and toggles a "closed for break" mode.

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

Everything server-side is in **[app.py](app.py)** (~500 lines): config, DB layer, utility functions, and all routes. There are no blueprints or modules to chase.

**Two-role model.** Anyone can `GET /`. Admin actions require a session flag set by `POST /login`. The `@admin_required` decorator (returns JSON 401) guards every mutating route. `is_admin()` reads `session["is_admin"]` and is passed into the template to switch the UI between guest and admin views.

**CRUD is fetch + full reload.** All mutations (`/fruits/add`, `/fruits/<id>/edit`, `/fruits/<id>/delete`, `/break/save`, `/break/off`) are `POST` endpoints returning `{"ok": bool, "error": str}` JSON. [static/app.js](static/app.js) submits forms via `fetch`, then on success calls `window.location.reload()` — there is no client-side state to keep in sync, so server-rendered HTML is always the source of truth.

**Server→client data handoff.** [templates/index.html](templates/index.html) injects `window.FRUITS = {{ fruits | tojson }}` and `window.BREAK = {{ brk | tojson }}` so JS can pre-fill the edit/break modals. Search is **purely client-side**: each card carries a `data-search` attribute (`name + origin`, lowercased) that `runSearch()` filters by hiding cards — no server roundtrip.

**SQLite, two tables**, file at `data/fruits.db` (gitignored, auto-created):
- `fruits` — the price-list rows. Seeded with 12 sample fruits on first run if empty.
- `settings` — a generic key/value table. Used only for the "Tạm nghỉ" (closed-for-break) feature via keys `break_enabled`, `break_until`, `break_message`, accessed through `get_setting`/`set_setting` and bundled by `get_break()`.

`init_db()` is called **at module top level**, not inside `if __name__ == "__main__"`. This is deliberate so WSGI deployment (PythonAnywhere/gunicorn, which import `app` and never run `__main__`) still initializes the DB. Don't move it.

**Provinces / origin dropdown.** At startup `load_provinces()` parses the Markdown table in `data/tinh_thanh_viet_nam_34*.md` (Vietnam's 34 post-2025-merger provinces) into `ORIGIN_OPTIONS`, prefixed with `"Nhập khẩu"` (imported). The origin `<select>` is populated from this list. If that file is missing or renamed, the dropdown only offers "Nhập khẩu".

**Vietnamese NFC normalization.** All text input passes through `nfc()` (Unicode NFC). This matters: the two status strings `"Còn bán"` / `"Hết hàng"` (constants `STATUS_AVAILABLE` / `STATUS_SOLD_OUT`) drive the sold-out styling, and NFD-vs-NFC mismatches would silently break the equality check. Use these constants rather than literal strings when comparing status.

**Image uploads.** `save_uploaded_image()` validates the extension (`png/jpg/jpeg/gif/webp`, 8MB cap via `MAX_CONTENT_LENGTH`), renames to a `uuid4().hex` filename, and stores under `static/uploads/` (gitignored except `.gitkeep`). Editing with a new image deletes the old file; deleting a fruit deletes its image.

## Deployment

`wsgi_pythonanywhere.py` is a **template**, not a runnable file — it documents the WSGI entry point (`from app import app as application`) and where to set the env-var secrets on the server. See `HUONG_DAN_PYTHONANYWHERE.md` for the full PythonAnywhere walkthrough.

## Runtime data is not tracked

`data/fruits.db` and `static/uploads/*` are gitignored. To reset to the 12 seed fruits, delete `data/fruits.db` and restart. The design reference `bich-trai-cay.html` at the repo root is kept for reference only and is not served.
