#!/usr/bin/env python3
"""Local HTTP receiver for CI test reports.

Listens for POST /report, validates the JSON and saves it as test-report.json
(the latest report). A copy of every report is also kept in received_reports/.

Usage:
  python receiver/receiver.py                    # http://127.0.0.1:8000
  python receiver/receiver.py --port 9000
Optional:  set RECEIVER_TOKEN to require the X-Report-Token header.
"""
import argparse
import hmac
import json
import os
import re
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
REQUIRED_KEYS = ("repository", "branch", "commit_sha", "pipeline_run_id",
                 "executed_at", "overall_status", "summary", "tests")
MAX_BODY = 2 * 1024 * 1024  # 2 MB


class ReportHandler(BaseHTTPRequestHandler):
    output_file = HERE / "test-report.json"
    archive_dir = HERE / "received_reports"
    token = None

    def _send(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/health"):
            self._send(200, {"status": "ok", "message": "Report receiver is running. POST reports to /report"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/report":
            return self._send(404, {"error": "POST to /report"})

        if self.token:
            supplied = self.headers.get("X-Report-Token", "")
            if not hmac.compare_digest(supplied, self.token):
                return self._send(401, {"error": "invalid token"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self._send(400, {"error": "bad Content-Length"})
        if length <= 0 or length > MAX_BODY:
            return self._send(413 if length > MAX_BODY else 400, {"error": "empty or too large body"})

        try:
            report = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._send(400, {"error": "body is not valid JSON"})

        if not isinstance(report, dict):
            return self._send(400, {"error": "report must be a JSON object"})
        missing = [key for key in REQUIRED_KEYS if key not in report]
        if missing:
            return self._send(400, {"error": "missing keys: " + ", ".join(missing)})

        text = json.dumps(report, indent=2)

        # 1) latest report -> test-report.json (written atomically)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.output_file.with_suffix(".json.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self.output_file)

        # 2) archive copy so every run (pass and fail) is kept for the demo
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")  # microseconds: no overwrite within a second
        sha = re.sub(r"[^0-9a-zA-Z]", "", str(report["commit_sha"]))[:7]
        status = re.sub(r"[^0-9a-zA-Z]", "", str(report["overall_status"])).lower()
        (self.archive_dir / ("%s_%s_%s.json" % (stamp, sha, status))).write_text(text, encoding="utf-8")

        s = report["summary"] if isinstance(report["summary"], dict) else {}
        print("[%s] RECEIVED run=%s commit=%s status=%s total=%s passed=%s failed=%s -> %s" % (
            datetime.now().strftime("%H:%M:%S"), report["pipeline_run_id"], sha,
            report["overall_status"], s.get("total"), s.get("passed"), s.get("failed"), self.output_file,
        ), flush=True)
        self._send(200, {"status": "saved", "file": self.output_file.name})

    def log_message(self, fmt, *args):  # quieter default logging
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    parser = argparse.ArgumentParser(description="Local CI test-report receiver")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--output", default=str(HERE / "test-report.json"), help="where to save the latest report")
    args = parser.parse_args()

    ReportHandler.output_file = Path(args.output).resolve()
    ReportHandler.archive_dir = ReportHandler.output_file.parent / "received_reports"
    ReportHandler.token = os.environ.get("RECEIVER_TOKEN") or None

    server = ThreadingHTTPServer((args.host, args.port), ReportHandler)
    print("Receiver listening on http://%s:%d/report" % (args.host, args.port))
    print("Saving latest report to: %s" % ReportHandler.output_file)
    print("Token protection: %s" % ("ON" if ReportHandler.token else "OFF"))
    print("Press Ctrl+C to stop.\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
