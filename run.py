import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    # host=0.0.0.0 便于局域网调试；公网请用云平台 + gunicorn 部署
    app.run(host="0.0.0.0", port=port, debug=debug)
