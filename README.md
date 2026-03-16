# Expense Tracker Application

This is a Flask-based expense tracking system with OCR, SMS parsing, charts, AI insights, and a chatbot.

## Features

- Add expenses manually, via receipt image, or SMS text.
- Visualize spending with pie/bar charts and filters.
- AI-powered insights and custom alerts.
- User profile with name, income, target, and avatar.
- Chatbot for answering questions about your expenses.

## AI Chatbot Setup

To enable the chatbot, install the OpenAI Python client and set the API key:

```bash
pip install openai
export OPENAI_API_KEY="your_key_here"  # Windows: setx OPENAI_API_KEY "your_key_here"
```

The `/chat` endpoint will automatically query GPT-3.5-turbo with your expenses data. If the key is missing or the package is unavailable, the chatbot falls back to basic keyword rules.
