# Expense Tracker — Restructure Plan (Flask + HTMX)

## Goal
Drop the Node/Tailwind-build toolchain. Move to server-rendered Flask + Jinja + HTMX
for all CRUD interactions, with Tailwind via CDN (no build step) for styling.

## Why
- App is fundamentally CRUD (add/edit/delete expenses, view/filter, set targets).
- HTMX handles partial page swaps without a JS framework or bundler.
- CDN Tailwind removes `package.json`, `package-lock.json`, `tailwind.config.js`,
  and the `npm install` / build step entirely — one less moving part for a
  Python-only deploy (matters for your Dockerfile too, smaller image, no Node stage).

## Files to remove
- `package.json`
- `package-lock.json`
- `tailwind.config.js`
- any `node_modules/`, `.npm` cache references in `.gitignore`/Dockerfile

## Files to add/change
- `app/templates/base.html` — add Tailwind CDN `<script>` tag + HTMX `<script>` tag in `<head>`
- `app/templates/partials/` — new folder for HTMX-swappable fragments (see below)
- `Dockerfile` — remove any Node/npm build stage, keep single Python stage

---

## 1. Dependency changes

**`app/templates/base.html` `<head>`:**
```html
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
```

**`requirements.txt`** — unchanged (Flask, Tesseract bindings, etc. stay as-is)

---

## 2. Route structure (in `app/routes.py`)

Split routes into "full page" vs "partial" (HTMX) responses:

| Route | Method | Returns | Purpose |
|---|---|---|---|
| `/expenses` | GET | full page | Dashboard shell, loads table via HTMX on load |
| `/expenses/table` | GET | partial | Expense table rows (filtered/sorted), swapped via HTMX |
| `/expenses/new` | GET | partial | Add-expense form (modal or inline row) |
| `/expenses` | POST | partial | Create expense, return updated table row(s) |
| `/expenses/<id>/edit` | GET | partial | Edit form for a row |
| `/expenses/<id>` | PUT/PATCH | partial | Update expense, return updated row |
| `/expenses/<id>` | DELETE | partial (empty/204) | Delete, HTMX removes row via `hx-swap="outerHTML swap:1s"` |
| `/receipts/scan` | POST | partial | OCR result → prefilled form fields |
| `/sms/parse` | POST | partial | Parsed SMS → prefilled form fields |
| `/analytics` | GET | full page | Charts page |
| `/targets` | GET/POST | partial | Monthly target form + status |

**Pattern:** every mutating route (`POST`/`PUT`/`DELETE`) returns just the
HTML fragment that needs to replace/append in the DOM — not a redirect,
not JSON (unless feeding a chart).

---

## 3. Template structure

```
app/templates/
├── base.html                  # layout, nav, CDN script tags
├── dashboard.html              # extends base, has empty <div hx-get="/expenses/table" hx-trigger="load">
├── analytics.html               # charts page
└── partials/
    ├── expense_table.html      # full <table> body, re-rendered on every filter/sort
    ├── expense_row.html        # single <tr>, used for insert/update via HTMX OOB swap
    ├── expense_form.html        # add/edit form, used inline or in a modal
    ├── receipt_upload_result.html
    ├── sms_parse_result.html
    └── target_status.html
```

**Key HTMX patterns to use:**
- `hx-get="/expenses/table" hx-trigger="load"` — load table on dashboard load
- `hx-post="/expenses" hx-target="#expense-table tbody" hx-swap="afterbegin"` — add row without reload
- `hx-delete="/expenses/{{id}}" hx-target="closest tr" hx-swap="outerHTML swap:0.3s"` — delete with fade
- `hx-get="/expenses/{{id}}/edit" hx-target="closest tr" hx-swap="outerHTML"` — inline edit
- `hx-post="/receipts/scan" hx-target="#expense-form" hx-encoding="multipart/form-data"` — OCR prefill
- Use `hx-indicator` for a small spinner during OCR/SMS parse (those take a moment)

---

## 4. Charts (Visual Analytics)

Charts stay JS-rendered (Chart.js via CDN, not HTMX — HTMX doesn't help here).
Fetch chart data as JSON from a dedicated endpoint (`/analytics/data`) and
render client-side. Keep this separate from the CRUD/HTMX flow.

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

---

## 5. Migration steps (order matters)

1. Add Tailwind CDN + HTMX `<script>` tags to `base.html`; confirm existing pages
   still render (Tailwind CDN reads classes at runtime, no purge needed for a small app).
2. Delete `package.json`, `package-lock.json`, `tailwind.config.js`. Update `.gitignore`
   to drop `node_modules`.
3. Update `Dockerfile` — remove any `npm install` / `npm run build` stage if present.
4. Refactor `routes.py`: split each CRUD route into full-page + partial variants
   per the table above. Keep `models.py`/`utils.py` untouched — only the route layer
   and templates change.
5. Build `partials/expense_row.html` and `partials/expense_table.html` first —
   this is the core CRUD loop. Get add/edit/delete working with HTMX before touching
   OCR/SMS.
6. Wire `receipts/scan` and `sms/parse` to return prefilled form partials.
7. Wire `targets` as its own small HTMX form + status partial.
8. Leave `analytics.html` mostly as-is; just confirm Chart.js CDN still loads
   correctly alongside Tailwind/HTMX.
9. Manual test pass: add/edit/delete expense, OCR upload, SMS paste, target set,
   confirm no full-page reloads except initial dashboard load.
10. Remove any now-dead static JS that duplicated what HTMX now handles
    (e.g., old fetch()-based add/delete handlers in `static/js/`).

---

## 6. Nice-to-haves (optional, after core migration works)
- `hx-boost="true"` on `<body>` in `base.html` for smooth nav between full pages
  (dashboard ↔ analytics) without HTMX-izing every single link.
- `hx-push-url="true"` on filter/sort controls so filtered views are bookmarkable.
- Toast/flash partial (`partials/toast.html`) returned via `HX-Trigger` header
  for success/error messages after CRUD ops.
