def version_1():
    from .package import create_app

    app = create_app()
    app.run(host="0.0.0.0", port=7070)

    return app


def version_2():
    from .package import create_app

    app = create_app()
    app.run(host="127.0.0.1", port=7171)

    return app
