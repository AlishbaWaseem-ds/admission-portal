"""Assignment Submission Portal (Flask)."""
import os

from flask import Flask, jsonify, redirect, render_template, request, url_for

from storage import SubmissionStore
from validation import validate_submission

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_FILE = os.path.join(BASE_DIR, "data", "submissions.json")


def create_app(data_file=None):
    app = Flask(__name__)
    app.config["DATA_FILE"] = (
        data_file or os.environ.get("SUBMISSIONS_FILE") or DEFAULT_DATA_FILE
    )
    store = SubmissionStore(app.config["DATA_FILE"])

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            submissions=list(reversed(store.all())),  # newest first
            errors={},
            form={},
            saved=request.args.get("saved") == "1",
        )

    @app.post("/submit")
    def submit():
        cleaned, errors = validate_submission(request.form)
        if errors:
            # Rejected: nothing is saved, the form is shown again with messages.
            return (
                render_template(
                    "index.html",
                    submissions=list(reversed(store.all())),
                    errors=errors,
                    form=request.form,
                    saved=False,
                ),
                400,
            )
        store.add(cleaned)
        return redirect(url_for("index", saved=1))

    @app.get("/api/submissions")
    def api_submissions():
        return jsonify(store.all())

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    create_app().run(host="127.0.0.1", port=port)
