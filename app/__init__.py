from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from config import Config

db            = SQLAlchemy()
migrate       = Migrate()
login_manager = LoginManager()
bcrypt        = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view             = 'auth.login'
    login_manager.login_message          = 'Please login to access this page'
    login_manager.login_message_category = 'warning'

    from app.models import User, Job, Skill, JobSkill, UserSkill, Application

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import main
    app.register_blueprint(main)

    from app.auth import auth
    app.register_blueprint(auth)

    # Make current_user available in all templates
    from flask_login import current_user

    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)

    return app