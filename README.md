# Expense Tracking Application

A modern, responsive Flask-based expense tracker featuring manual entry, receipt OCR, SMS parsing, and visual insights.

## Features

- **Responsive Dashboard**: Track your spending at a glance.
- **Receipt OCR**: Upload receipt images to automatically extract merchant, date, and amount using Tesseract OCR.
- **SMS Parsing**: Paste transaction SMS text to quickly add expenses.
- **Visual Analytics**: Interactive pie and bar charts for category-wise and date-wise spending analysis.
- **AI Chatbot**: Optional integration with OpenAI for asking questions about your spending.
- **Monthly Targets**: Set and monitor monthly spending limits.

## Prerequisites

- **Python 3.10+**
- **Tesseract OCR**: Required for receipt scanning.
  - [Download Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki)
  - Install to `C:\Program Files\Tesseract-OCR` (default location)

## Setup Instructions

1. **Clone the Repository**

   ```bash
   git clone <your-repository-url>
   cd expense-track
   ```

2. **Create a Virtual Environment**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**

   ```powershell
   pip install -r requirements.txt
   ```

4. **Initialize the Database**

   ```powershell
   python scripts/init_db.py
   ```

5. **Configure VS Code (Recommended)**
   - The project includes a `.vscode/settings.json` to automatically detect the virtual environment.
   - If prompted, select the Python Interpreter located at `.venv\Scripts\python.exe`.

6. **Run the Application**
   ```powershell
   python run.py
   ```
   Open `http://127.0.0.1:5000` in your browser.

## Project Structure

- `app/`: The core application package.
  - `models.py`: Database schema.
  - `routes.py`: Flask Blueprints and routes.
  - `utils.py`: OCR, parsing, and analytics logic.
  - `static/`: Frontend assets (CSS, JS, images).
  - `templates/`: HTML templates.
- `docs/`: Supplementary guides (e.g., Tesseract Installation).
- `scripts/`: Initialization and maintenance scripts.
- `run.py`: The entry point script to start the server.
- `uploads/`: Storage for processed receipt images.

## Documentation

- [Tesseract OCR Installation Guide](docs/TESSERACT_INSTALLATION.md)

## License

This project is licensed under the [MIT License](LICENSE).
