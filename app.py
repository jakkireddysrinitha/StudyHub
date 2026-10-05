from flask import Flask, render_template

from src.routes import api


app = Flask(__name__)

app.register_blueprint(
    api,
    url_prefix="/api"
)


@app.route("/")
def home():
    return render_template(
        "index.html"
    )


@app.errorhandler(404)
def not_found(error):
    if "/api/" in getattr(
        error,
        "description",
        ""
    ):
        return {
            "error": "API endpoint not found"
        }, 404

    return error


@app.errorhandler(500)
def internal_error(error):
    return {
        "error": "Internal server error"
    }, 500


if __name__ == "__main__":
    app.run(
        debug=True,
        use_reloader=False
    )