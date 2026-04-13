from __future__ import annotations

from app import app, bootstrap_models


if __name__ == "__main__":
    bootstrap_models()
    app.run(host="127.0.0.1", port=5001, debug=True)
