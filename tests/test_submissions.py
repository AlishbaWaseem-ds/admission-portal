"""Automated tests for the assignment submission portal."""
import os
import shutil
import tempfile
import unittest

from app import create_app
from storage import SubmissionStore

VALID_FORM = {
    "student_name": "Ayesha Khan",
    "registration_number": "FA22-BSE-001",
    "assignment_title": "DevOps Lab 1",
    "submission_url": "https://github.com/ayesha/devops-lab1",
}


class SubmissionPortalTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.tmpdir, "submissions.json")
        self.client = create_app(self.data_file).test_client()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def saved(self):
        return SubmissionStore(self.data_file).all()

    # ---- the three required test cases -------------------------------------

    def test_valid_submission_is_saved_and_listed(self):
        """Complete details and a valid URL: submission is saved and appears in the list."""
        response = self.client.post("/submit", data=VALID_FORM, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        saved = self.saved()
        self.assertEqual(len(saved), 1, "Exactly one submission should be saved")
        self.assertEqual(saved[0]["registration_number"], "FA22-BSE-001")

        page = response.get_data(as_text=True)
        self.assertIn("Submission saved successfully", page)
        self.assertIn("Ayesha Khan", page)
        self.assertIn("DevOps Lab 1", page)
        self.assertIn("https://github.com/ayesha/devops-lab1", page)

    def test_missing_registration_number_is_rejected(self):
        """Missing registration number: submission is rejected with a validation message."""
        form = dict(VALID_FORM, registration_number="")
        response = self.client.post("/submit", data=form)
        self.assertEqual(
            response.status_code, 400,
            "A submission without a registration number must be rejected",
        )
        self.assertIn("Registration number is required", response.get_data(as_text=True))
        self.assertEqual(self.saved(), [], "A rejected submission must not be saved")

    def test_invalid_submission_url_is_not_saved(self):
        """Invalid submission URL: submission is rejected and not saved."""
        bad_urls = [
            "not-a-url",
            "github.com/user/repo",
            "ftp://example.com/file.zip",
            "javascript:alert(1)",
            "http://",
            "https://exa mple.com",
        ]
        for bad_url in bad_urls:
            form = dict(VALID_FORM, submission_url=bad_url)
            response = self.client.post("/submit", data=form)
            self.assertEqual(
                response.status_code, 400, "URL should be rejected: %r" % bad_url
            )
            self.assertIn("Submission URL is invalid", response.get_data(as_text=True))
        self.assertEqual(self.saved(), [], "Invalid URLs must never be saved")

    # ---- additional tests --------------------------------------------------

    def test_missing_student_name_is_rejected(self):
        """Missing student name: submission is rejected."""
        response = self.client.post("/submit", data=dict(VALID_FORM, student_name="   "))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Student name is required", response.get_data(as_text=True))
        self.assertEqual(self.saved(), [])

    def test_missing_assignment_title_is_rejected(self):
        """Missing assignment title: submission is rejected."""
        response = self.client.post("/submit", data=dict(VALID_FORM, assignment_title=""))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Assignment title is required", response.get_data(as_text=True))
        self.assertEqual(self.saved(), [])

    def test_home_page_loads_with_empty_list(self):
        """Home page loads and shows an empty submission list."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("No submissions yet", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
