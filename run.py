import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    is_debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1")
    app.run(debug=is_debug)
