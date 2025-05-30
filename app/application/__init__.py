from flask import Flask


def create_app():
    """ Initialize the core application """
    app = Flask(__name__, instance_relative_config=False)
    # app.config.from_object('config.Config')

    # Initialize plugins
    # none at the moment

    with app.app_context():
        from . import routes

        return app

