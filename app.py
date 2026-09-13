from flask import Flask

from db import init_db
from routes.months import bp as months_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = "dev-local-only"
    init_db()
    app.register_blueprint(months_bp)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5050)
