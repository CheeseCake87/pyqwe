from flask import Flask


def create_app():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return 'Hello, World!'

    return app


def run():
    app = create_app()
    app.run()
