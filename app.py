from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request
)

from flask_login import login_required, current_user

from src.config import (
    SECRET_KEY,
    DATABASE_FILE
)

from src.models import db

from src.auth import (
    auth,
    login_manager
)

from src.routes import api


app = Flask(__name__)


# --------------------------------------------------
# Flask configuration
# --------------------------------------------------

app.config["SECRET_KEY"] = SECRET_KEY

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{DATABASE_FILE.as_posix()}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


# --------------------------------------------------
# Extensions
# --------------------------------------------------

db.init_app(app)

login_manager.init_app(app)


# --------------------------------------------------
# Blueprints
# --------------------------------------------------

app.register_blueprint(auth)

app.register_blueprint(
    api,
    url_prefix="/api"
)


# --------------------------------------------------
# Create database tables
# --------------------------------------------------

with app.app_context():
    db.create_all()


# --------------------------------------------------
# Home page
# --------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def home():

    # If something accidentally sends POST /
    # we handle it instead of returning 405.

    if request.method == "POST":

        if current_user.is_authenticated:
            return redirect(
                url_for("home")
            )

        return redirect(
            url_for("auth.login")
        )

    # Normal GET request

    if not current_user.is_authenticated:
        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "index.html"
    )


# --------------------------------------------------
# Error handlers
# --------------------------------------------------

@app.errorhandler(404)
def not_found(error):

    return {
        "error": "Page not found"
    }, 404


@app.errorhandler(500)
def internal_error(error):

    return {
        "error": "Internal server error"
    }, 500


# --------------------------------------------------
# Run application
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=True,
        use_reloader=False
    )