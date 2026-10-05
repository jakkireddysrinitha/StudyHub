from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from src.models import (
    db,
    User
)


auth = Blueprint(
    "auth",
    __name__
)


login_manager = LoginManager()

login_manager.login_view = "auth.login"

login_manager.login_message = None


@login_manager.user_loader
def load_user(user_id):

    try:
        return db.session.get(
            User,
            int(user_id)
        )

    except (
        TypeError,
        ValueError
    ):
        return None


# ==================================================
# REGISTER
# ==================================================

@auth.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # ------------------------------------------
        # Validation
        # ------------------------------------------

        if not username:

            flash(
                "Please enter a username.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if len(username) < 3:

            flash(
                "Username must be at least 3 characters.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not email:

            flash(
                "Please enter your email.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if not password:

            flash(
                "Please enter a password.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if len(password) < 6:

            flash(
                "Password must be at least 6 characters.",
                "error"
            )

            return render_template(
                "register.html"
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return render_template(
                "register.html"
            )

        # ------------------------------------------
        # Check duplicate username
        # ------------------------------------------

        existing_username = User.query.filter_by(
            username=username
        ).first()

        if existing_username:

            flash(
                "That username is already taken.",
                "error"
            )

            return render_template(
                "register.html"
            )

        # ------------------------------------------
        # Check duplicate email
        # ------------------------------------------

        existing_email = User.query.filter_by(
            email=email
        ).first()

        if existing_email:

            flash(
                "An account with that email already exists.",
                "error"
            )

            return render_template(
                "register.html"
            )

        # ------------------------------------------
        # Create user
        # ------------------------------------------

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(
                password
            )
        )

        db.session.add(
            user
        )

        db.session.commit()

        flash(
            "Account created successfully. Please log in.",
            "success"
        )

        return redirect(
            url_for(
                "auth.login"
            )
        )

    # GET /register

    return render_template(
        "register.html"
    )


# ==================================================
# LOGIN
# ==================================================

@auth.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if current_user.is_authenticated:

        return redirect(
            url_for("home")
        )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Please enter your email and password.",
                "error"
            )

            return render_template(
                "login.html"
            )

        user = User.query.filter_by(
            email=email
        ).first()

        if not user:

            flash(
                "Invalid email or password.",
                "error"
            )

            return render_template(
                "login.html"
            )

        if not check_password_hash(
            user.password_hash,
            password
        ):

            flash(
                "Invalid email or password.",
                "error"
            )

            return render_template(
                "login.html"
            )

        login_user(
            user
        )

        # Flask-Login can provide ?next=/
        next_url = request.args.get(
            "next"
        )

        # Only allow local paths.
        if (
            next_url
            and next_url.startswith("/")
            and not next_url.startswith("//")
        ):

            return redirect(
                next_url
            )

        return redirect(
            url_for("home")
        )

    return render_template(
        "login.html"
    )


# ==================================================
# LOGOUT
# ==================================================

@auth.route(
    "/logout",
    methods=["GET", "POST"]
)
def logout():

    logout_user()

    return redirect(
        url_for("auth.login")
    )