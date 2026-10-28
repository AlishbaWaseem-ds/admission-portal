"""Tiny JSON-file storage for submissions."""
import json
import os
import threading
from datetime import datetime, timezone


class SubmissionStore:
    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()

    def _read(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    def all(self):
        """Return all saved submissions, oldest first."""
        with self._lock:
            return self._read()

    def add(self, submission):
        """Save one submission and return the stored record."""
        record = dict(submission)
        record["submitted_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        with self._lock:
            records = self._read()
            records.append(record)
            folder = os.path.dirname(self.path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            tmp_path = self.path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(records, handle, indent=2)
            os.replace(tmp_path, self.path)
        return record
