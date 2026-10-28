#!/usr/bin/env python3
"""Run the automated tests and write a JSON test report.

The report is built from the REAL results of executing the unittest suite.
Exit code is 0 when every test passes and 1 otherwise, so a failing test makes
the CI "test" step (and therefore the job) fail.

Usage:  python tools/run_tests.py [--output test-report.json]
"""
import argparse
import json
import os
import subprocess
import sys
import traceback
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class RecordingResult(unittest.TextTestResult):
    """Normal console output + a record of every test outcome."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    @staticmethod
    def _name(test):
        method = getattr(test, "_testMethodName", None)
        if method:
            return "%s.%s" % (type(test).__name__, method)
        return str(test)

    def _record(self, test, outcome, err=None, reason=None):
        message = None
        details = None
        if err is not None:
            message = "%s: %s" % (err[0].__name__, err[1])
            details = "".join(traceback.format_exception(*err))[-3000:]
        elif reason:
            message = reason
        self.records.append(
            {
                "name": self._name(test),
                "description": test.shortDescription() if hasattr(test, "shortDescription") else None,
                "result": outcome,
                "message": message,
                "details": details,
            }
        )

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, "failed", err=err)

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test, "failed", err=err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test, "skipped", reason=reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._record(test, "passed", reason="Expected failure")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._record(test, "failed", reason="Unexpected success")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self._record(subtest, "failed", err=err)


def git(*args):
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def build_metadata():
    env = os.environ
    repo = env.get("GITHUB_REPOSITORY")
    run_id = env.get("GITHUB_RUN_ID")
    server = env.get("GITHUB_SERVER_URL", "https://github.com")
    return {
        "repository": repo or ROOT.name,
        "branch": env.get("GITHUB_REF_NAME") or git("rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        "commit_sha": env.get("GITHUB_SHA") or git("rev-parse", "HEAD") or "unknown",
        "pipeline_run_id": run_id or "local-run",
        "pipeline_run_number": env.get("GITHUB_RUN_NUMBER"),
        "pipeline_url": "%s/%s/actions/runs/%s" % (server, repo, run_id) if repo and run_id else None,
        "executed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default=str(ROOT / "test-report.json"))
    parser.add_argument("--start-dir", default="tests")
    args = parser.parse_args()

    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))

    suite = unittest.defaultTestLoader.discover(
        args.start_dir, pattern="test*.py", top_level_dir=str(ROOT)
    )
    runner = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult)
    result = runner.run(suite)

    tests = result.records
    passed = sum(1 for t in tests if t["result"] == "passed")
    failed = sum(1 for t in tests if t["result"] == "failed")
    skipped = sum(1 for t in tests if t["result"] == "skipped")
    total = len(tests)
    overall = "PASSED" if total > 0 and failed == 0 else "FAILED"

    report = build_metadata()
    report.update(
        {
            "overall_status": overall,
            "summary": {"total": total, "passed": passed, "failed": failed, "skipped": skipped},
            "tests": tests,
        }
    )

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("\nReport written to %s" % args.output)
    print("Overall: %s  (total=%d passed=%d failed=%d skipped=%d)" % (overall, total, passed, failed, skipped))
    return 0 if overall == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
