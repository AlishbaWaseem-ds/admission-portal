#!/usr/bin/env python3
"""E-mail the test report (bonus task). Credentials come from environment variables / CI secrets.

Environment variables:
  EMAIL_TO         recipient address (configurable)           [required]
  SMTP_USERNAME    SMTP login, e.g. your Gmail address        [required]
  SMTP_PASSWORD    SMTP password / Gmail App Password         [required]
  SMTP_HOST        default smtp.gmail.com
  SMTP_PORT        default 587 (STARTTLS); 465 uses SSL
  EMAIL_FROM       default = SMTP_USERNAME

If EMAIL_TO / SMTP_USERNAME / SMTP_PASSWORD are missing the step is skipped (exit 0).

Usage:  python tools/email_report.py test-report.json
"""
import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage


def build_message(report, sender, recipient):
    summary = report.get("summary", {})
    status = report.get("overall_status", "UNKNOWN")
    sha = str(report.get("commit_sha", "unknown"))
    repo = report.get("repository", "unknown")

    subject = "[%s] %s @ %s - %s/%s tests passed" % (
        status, repo, sha[:7], summary.get("passed", 0), summary.get("total", 0),
    )

    lines = [
        "Test report for %s" % repo,
        "",
        "Overall result : %s" % status,
        "Branch         : %s" % report.get("branch"),
        "Commit         : %s" % sha,
        "Pipeline run   : %s" % report.get("pipeline_run_id"),
        "Run URL        : %s" % (report.get("pipeline_url") or "n/a"),
        "Executed at    : %s" % report.get("executed_at"),
        "",
        "Total: %s   Passed: %s   Failed: %s   Skipped: %s" % (
            summary.get("total"), summary.get("passed"), summary.get("failed"), summary.get("skipped", 0),
        ),
        "",
        "Individual results:",
    ]
    for test in report.get("tests", []):
        mark = {"passed": "PASS", "failed": "FAIL"}.get(test.get("result"), "SKIP")
        lines.append("  [%s] %s" % (mark, test.get("name")))
        if test.get("message"):
            lines.append("         -> %s" % test["message"])
    lines += ["", "The full JSON report is attached."]

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content("\n".join(lines))
    message.add_attachment(
        json.dumps(report, indent=2).encode("utf-8"),
        maintype="application", subtype="json", filename="test-report.json",
    )
    return message


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "test-report.json"
    recipient = os.environ.get("EMAIL_TO", "").strip()
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    if not (recipient and username and password):
        print("Email not configured (EMAIL_TO / SMTP_USERNAME / SMTP_PASSWORD missing) - skipping.")
        return 0

    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.environ.get("SMTP_PORT") or "587")
    sender = (os.environ.get("EMAIL_FROM") or "").strip() or username

    with open(path, "r", encoding="utf-8") as handle:
        report = json.load(handle)
    message = build_message(report, sender, recipient)

    context = ssl.create_default_context()
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, context=context, timeout=30)
    else:
        server = smtplib.SMTP(host, port, timeout=30)
        server.starttls(context=context)
    with server:
        server.login(username, password)
        server.send_message(message)
    print("Report e-mailed to %s (%s)" % (recipient, message["Subject"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
