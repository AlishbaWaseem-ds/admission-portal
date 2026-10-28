"""Input validation for the assignment submission form."""
from urllib.parse import urlparse

FIELD_LABELS = {
    "student_name": "Student name",
    "registration_number": "Registration number",
    "assignment_title": "Assignment title",
    "submission_url": "Submission URL",
}


def is_valid_url(value):
    """Return True only for well-formed http:// or https:// links."""
    if not value or any(ch.isspace() for ch in value):
        return False
    try:
        parsed = urlparse(value)
        parsed.port  # raises ValueError for a malformed port
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    if host == "localhost":
        return True
    # a real host needs at least one dot, e.g. github.com
    return "." in host and not host.startswith(".") and not host.endswith(".")


def validate_submission(form):
    """Validate form data.

    Returns (cleaned_values, errors). `errors` is empty when the data is valid.
    """
    cleaned = {key: (form.get(key) or "").strip() for key in FIELD_LABELS}
    errors = {}

    if not cleaned["student_name"]:
        errors["student_name"] = "Student name is required."

    reg_no = cleaned["registration_number"]
    if not reg_no:
        errors["registration_number"] = "Registration number is required."

    if not cleaned["assignment_title"]:
        errors["assignment_title"] = "Assignment title is required."

    url = cleaned["submission_url"]
    if not url:
        errors["submission_url"] = "Submission URL is required."
    elif not is_valid_url(url):
        errors["submission_url"] = (
            "Submission URL is invalid. Enter a full link starting with http:// or https://"
        )

    return cleaned, errors
