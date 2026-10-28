#!/usr/bin/env python3
"""POST the JSON test report to the local receiver (through a tunnel or a local runner).

Environment variables:
  RECEIVER_URL    required, e.g. https://abc123.ngrok-free.app/report
                  (or http://localhost:8000/report when the runner is local)
  RECEIVER_TOKEN  optional shared secret, sent as the X-Report-Token header

Usage:  python tools/send_report.py test-report.json
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "test-report.json"
    url = (os.environ.get("RECEIVER_URL") or "").strip()
    if not url:
        print("ERROR: RECEIVER_URL is not set (add it as a GitHub secret).")
        return 2
    if not os.path.exists(path):
        print("ERROR: report file not found: %s" % path)
        return 2

    with open(path, "rb") as handle:
        body = handle.read()
    json.loads(body)  # make sure we only ever send valid JSON

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ci-report-sender/1.0",
        "ngrok-skip-browser-warning": "true",
    }
    token = os.environ.get("RECEIVER_TOKEN")
    if token:
        headers["X-Report-Token"] = token

    last_error = None
    for attempt in range(1, 4):
        try:
            request = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=20) as response:
                print("Receiver answered %s: %s" % (response.status, response.read().decode("utf-8", "replace")))
                return 0
        except urllib.error.HTTPError as err:
            last_error = "HTTP %s: %s" % (err.code, err.read().decode("utf-8", "replace"))
        except (urllib.error.URLError, OSError) as err:
            last_error = str(err)
        print("Attempt %d/3 failed: %s" % (attempt, last_error))
        time.sleep(3 * attempt)

    print("ERROR: could not deliver the report. Is the receiver and tunnel running?")
    return 1


if __name__ == "__main__":
    sys.exit(main())
