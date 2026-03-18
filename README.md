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
   python init_db.py
   ```

5. **Configure VS Code (Recommended)**
   - The project includes a `.vscode/settings.json` to automatically detect the virtual environment.
   - If prompted, select the Python Interpreter located at `.venv\Scripts\python.exe`.

6. **Run the Application**
   ```powershell
   python app.py
   ```
   Open `http://127.0.0.1:5000` in your browser.

## Project Structure

- `app.py`: Main application logic and API endpoints.
- `models.py`: Database schema for Expenses and User Profiles.
- `templates/`: HTML templates with a responsive design.
- `static/`: CSS, JavaScript, and user-uploaded avatars.
- `uploads/`: Temporary storage for receipt images during processing.

## License
MIT
