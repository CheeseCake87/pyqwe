from flask import Flask


def create_app():
    app_ = Flask(__name__)

    @app_.route("/")
    def hello():
        return "Hello, World!"

    return app_


def run():
    app_ = create_app()
    app_.run()


if __name__ == "__main__":
    app = create_app()
    app.run()
