"""Local development entry point. Run with: python app.py"""

import os
from food_rescue import create_app

app = create_app()

if __name__ == "__main__":
    # In production, set FLASK_DEBUG=False. Default to True for student local development.
    debug_mode = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    app.run(host="127.0.0.1", port=5000, debug=debug_mode)
