# Expense Tracking Application

[![CI](https://github.com/mit0506/expense-track/actions/workflows/ci.yml/badge.svg)](https://github.com/mit0506/expense-track/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![HTMX](https://img.shields.io/badge/HTMX-1.9.12-3366CC?style=flat&logo=htmx&logoColor=white)](https://htmx.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-CDN-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Pytest](https://img.shields.io/badge/Tests-Pytest%20(75%20passed)-0A9EDC?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-Integrated-412991?style=flat&logo=openai&logoColor=white)](https://openai.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A fast, responsive Flask-based personal finance and expense tracker powered by **HTMX** and **Tailwind CSS**. Features real-time search, inline editing, receipt OCR, transaction SMS parsing, bill splitting, subscription tracking, and visual analytics—with zero frontend build step.

![Dashboard Preview](assets/Dashboard%20-%20Expense%20Tracker.png)

---

## ✨ Features

- **⚡ Reactive HTMX UI**: Seamless dynamic updates (live search, category filters, pagination, inline editing, and row deletion) without page reloads.
- **🧾 Receipt OCR Scanning**: Upload receipt images to automatically extract merchant, date, and amount via Tesseract OCR.
- **💬 SMS Transaction Parsing**: Paste raw bank/card SMS alerts to auto-fill expense entries.
- **📊 Visual Analytics**: Interactive charts for category breakdowns, monthly budgets, and spending trends.
- **👥 Bill Splitting & Subscriptions**: Track shared expenses with friends and manage recurring subscription renewals.
- **🤖 AI Financial Chatbot**: Integrated OpenAI assistant to query your spending habits and gain financial insights.
- **🎯 Monthly Targets & Health Indicators**: Set category-level limits and visual progress dials.
- **🔒 Secure & Containerized**: Built-in CSRF protection, rate limiting, and single-stage Docker deployment.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate, Flask-Limiter
- **Frontend**: Jinja2 Templates, HTMX, Tailwind CSS (CDN), Custom Machined Tactile Theme
- **Data & OCR**: SQLite / MySQL / PostgreSQL (via SQLAlchemy), Pillow, Tesseract OCR
- **Testing & CI**: Pytest, GitHub Actions CI/CD (lightweight, automated test suite)
- **Container**: Docker (Python 3.14-slim base) & Docker Compose

---

## 📁 Project Structure

```text
expense-track/
├── app/
│   ├── routes/               # Modular Flask blueprints
│   │   ├── auth.py           # User authentication & registration
│   │   ├── expenses.py       # Expense CRUD, HTMX table/inline edit endpoints
│   │   ├── api.py            # JSON REST APIs & AI chatbot endpoints
│   │   ├── subscriptions.py  # Recurring subscriptions & bill split routes
│   │   └── __init__.py
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── partials/         # HTMX swappable HTML fragments
│   │   │   ├── expense_row.html        # Individual table row with inline triggers
│   │   │   ├── expense_row_edit.html   # Inline edit row form
│   │   │   ├── expense_table.html      # Searchable, filterable expense table
│   │   │   ├── receipt_upload_result.html # OCR result preview form
│   │   │   ├── sms_parse_result.html   # SMS parse result form
│   │   │   └── target_status.html      # Monthly budget & health metric dials
│   │   ├── base.html         # Base layout with HTMX & Tailwind CDN
│   │   └── index.html        # Main dashboard view
│   ├── static/
│   │   └── css/
│   │       └── custom.css    # Tactile theme variables & HTMX swap animations
│   ├── models.py             # SQLAlchemy database models
│   ├── utils.py              # OCR extraction, SMS parser, & analytics helpers
│   ├── validators.py         # Input validation & sanitization
│   ├── constants.py          # Category and payment method definitions
│   └── __init__.py           # Application factory & extension initialization
├── migrations/               # Alembic database migration scripts
├── scripts/                  # Helper & database initialization scripts
│   ├── init_db.py
│   └── generate_default_avatar.py
├── tests/                    # Pytest test suite (75+ unit & integration tests)
├── .env.example              # Template for environment variables
├── Dockerfile                # Single-stage Python container
├── docker-compose.yml        # Multi-container orchestration
├── requirements.txt          # Python dependencies
└── run.py                    # Application entrypoint
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Tesseract OCR** (required for receipt image scanning):
  - [Tesseract OCR Installation Guide](docs/TESSERACT_INSTALLATION.md)
  - [Download Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki)

---

### Local Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/mit0506/expense-track.git
   cd expense-track
   ```

2. **Create & Activate Virtual Environment**
   - **PowerShell**:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS / Git Bash**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Copy the example `.env` file and adjust your settings:
   ```bash
   cp .env.example .env
   ```
   *(On Windows PowerShell: `Copy-Item .env.example .env`)*

5. **Initialize Database**
   ```bash
   python scripts/init_db.py
   ```

6. **Run the Development Server**
   ```bash
   python run.py
   ```
   Access the app at: **`http://127.0.0.1:5000`**

---

## 🧪 Running Tests

Run the full automated test suite using `pytest`:

```bash
pytest tests/ -v --tb=short
```

---

## 🐳 Docker Deployment

You can run the full application using Docker and Docker Compose without manual Python setup:

1. **Build and Run with Docker Compose**
   ```bash
   docker compose up --build
   ```

2. Access the application at **`http://localhost:5173`** (or configured port).

---

## 📖 Documentation

- [Tesseract OCR Installation Guide](docs/TESSERACT_INSTALLATION.md)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
