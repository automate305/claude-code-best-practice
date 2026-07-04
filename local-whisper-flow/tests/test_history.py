import json
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from localflow.history import read_all, record


class TestHistory(unittest.TestCase):
    def test_record_and_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            record({"text": "hello", "words": 1}, path)
            record({"text": "world again", "words": 2}, path)
            entries = read_all(path)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["text"], "hello")
            self.assertEqual(entries[1]["words"], 2)

    def test_read_missing_file_returns_empty(self):
        self.assertEqual(read_all(Path("/nonexistent/history.jsonl")), [])

    def test_read_skips_corrupt_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            record({"text": "good"}, path)
            with path.open("a") as f:
                f.write("{truncated garba\n")
            record({"text": "also good"}, path)
            texts = [e["text"] for e in read_all(path)]
            self.assertEqual(texts, ["good", "also good"])


class TestDashboardServer(unittest.TestCase):
    def test_serves_page_and_history_api(self):
        from localflow.dashboard import start_dashboard

        server = start_dashboard(port=0)  # OS-assigned free port
        port = server.server_address[1]
        try:
            page = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read()
            self.assertIn(b"LocalFlow", page)
            api = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/history").read()
            self.assertIsInstance(json.loads(api), list)
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
