# Assignment Submission Portal (CSC418 DevOps - Lab Midterm)

A small Flask web app where students submit the **link** to an assignment, with
automated tests, a GitHub Actions CI pipeline, and a local receiver that stores
the CI test report as `test-report.json`.

```
app.py / validation.py / storage.py   the portal (Flask + JSON file storage)
templates/index.html                  the web page
static/colors.css                     all colours (shared by the portal and the static demo)
tests/test_submissions.py             automated tests (unittest)
tools/run_tests.py                    runs the tests and writes the JSON report
tools/send_report.py                  CI -> POST report to the local receiver
tools/email_report.py                 (bonus) e-mail the report
receiver/receiver.py                  local HTTP receiver -> saves test-report.json
static_demo/index.html                (bonus) static demo published to GitHub Pages
.github/workflows/ci.yml              the CI pipeline
```

## 1. Run the application

Requires Python 3.9+.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5001>. Submissions are stored in `data/submissions.json`.
(Change the port with the `PORT` environment variable.)

## 2. Run the automated tests

```bash
python -m unittest discover -s tests -t . -v      # plain test run
python tools/run_tests.py                         # test run + writes test-report.json
```

`tools/run_tests.py` exits with code 1 if any test fails (this is what makes the CI test stage fail).

Tests included:

| Test | Expected result |
|------|-----------------|
| `test_valid_submission_is_saved_and_listed` | complete details + valid URL -> saved and shown in the list |
| `test_missing_registration_number_is_rejected` | rejected (HTTP 400) with a validation message, nothing saved |
| `test_invalid_submission_url_is_not_saved` | rejected and not saved |
| `test_missing_student_name_is_rejected`, `test_missing_assignment_title_is_rejected`, `test_home_page_loads_with_empty_list` | extra checks |

## 3. Start the local report receiver

```bash
python receiver/receiver.py            # listens on http://127.0.0.1:8000/report
```

Every report posted by CI is saved as `receiver/test-report.json` (latest run) and a copy is
kept in `receiver/received_reports/`. Optional protection: set `RECEIVER_TOKEN` before starting
the receiver and put the same value in the `RECEIVER_TOKEN` GitHub secret.

### Reaching the receiver from GitHub (connectivity)

A GitHub-hosted runner cannot see your `localhost`. Choose ONE:

**A. Tunnel (default)** - keep the receiver and the tunnel running:

```bash
python receiver/receiver.py
ngrok http 8000            # or: cloudflared tunnel --url http://localhost:8000
```

Put the public URL + `/report` into the `RECEIVER_URL` secret, e.g. `https://abcd.ngrok-free.app/report`.

> A quick tunnel (`cloudflared tunnel --url ...` or ngrok without a static domain) gets a **new URL
> every time it starts**. After restarting it, update the `RECEIVER_URL` secret. Cloudflare error
> `530 / 1033` in the CI log means the tunnel behind the URL is not running. ngrok's free static
> domain (`ngrok http --url=<your-domain> 8000`) keeps the same URL between restarts.

**B. Local runner** - install a GitHub *self-hosted runner* on your PC
(Settings -> Actions -> Runners -> New self-hosted runner), start it, create the repository
variable `CI_RUNNER` = `self-hosted` and set `RECEIVER_URL` = `http://localhost:8000/report`.

## 4. CI pipeline (`.github/workflows/ci.yml`)

On every push to any branch:

1. **test** - installs dependencies, runs `tools/run_tests.py`, uploads `test-report.json`. A failing test fails this job.
2. **report** - runs after passing *and* failing tests; POSTs the report to the receiver and (bonus) e-mails it.
3. **deploy** (bonus) - only on `main` and only if **test** succeeded: publishes `static_demo/` to GitHub Pages.

### Repository secrets

| Secret | Purpose |
|--------|---------|
| `RECEIVER_URL` | public (tunnel) or local URL of the receiver, ending in `/report` |
| `RECEIVER_TOKEN` | optional shared token (must match the receiver's `RECEIVER_TOKEN`) |
| `EMAIL_TO` | (bonus) address that receives the report |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | (bonus) SMTP login - for Gmail use an *App Password* |
| `SMTP_HOST` / `SMTP_PORT` | optional, default `smtp.gmail.com` / `587` |

Gmail App Password: turn on 2-Step Verification, then create one at
<https://myaccount.google.com/apppasswords> and paste the 16-character code into `SMTP_PASSWORD`.

GitHub Pages: Settings -> Pages -> Source = **GitHub Actions**.

## Demonstration (pass -> fail -> fix)

1. Start the receiver and the tunnel, check the `RECEIVER_URL` secret, then push. All jobs are green and
   `receiver/test-report.json` shows `"overall_status": "PASSED"`.
2. Introduce a defect, e.g. delete the registration-number check in `validation.py`, and push.
   The **test** job fails, the report job still delivers `test-report.json` with `"FAILED"` and the
   failure message, and **deploy** is skipped (the published Pages site stays unchanged).
3. Restore the check and push again: everything is green and the JSON shows `PASSED`.

## 5. Report format (`test-report.json`)

```json
{
  "repository": "user/assignment-portal",
  "branch": "main",
  "commit_sha": "…",
  "pipeline_run_id": "…",
  "pipeline_run_number": "…",
  "pipeline_url": "https://github.com/user/assignment-portal/actions/runs/…",
  "executed_at": "2026-10-27T16:26:05+00:00",
  "overall_status": "PASSED | FAILED",
  "summary": { "total": 6, "passed": 6, "failed": 0, "skipped": 0 },
  "tests": [
    { "name": "…", "description": "…", "result": "passed | failed", "message": null, "details": null }
  ]
}
```
