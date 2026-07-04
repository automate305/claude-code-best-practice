import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from localflow.config import DEFAULTS, load_config, parse_hotkey


class TestLoadConfig(unittest.TestCase):
    def test_first_run_writes_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "localflow" / "config.json"
            config = load_config(path)
            self.assertEqual(config, DEFAULTS)
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text()), DEFAULTS)

    def test_user_values_override_defaults_and_missing_keys_fall_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"model": "tiny", "hotkey": "ctrl+alt"}))
            config = load_config(path)
            self.assertEqual(config["model"], "tiny")
            self.assertEqual(config["hotkey"], "ctrl+alt")
            self.assertEqual(config["inject_mode"], DEFAULTS["inject_mode"])


class TestParseHotkey(unittest.TestCase):
    def test_single_key(self):
        self.assertEqual(parse_hotkey("f9"), frozenset({"f9"}))

    def test_combo_is_normalized(self):
        self.assertEqual(parse_hotkey(" Ctrl + Alt "), frozenset({"ctrl", "alt"}))

    def test_empty_spec_raises(self):
        with self.assertRaises(ValueError):
            parse_hotkey(" + ")


if __name__ == "__main__":
    unittest.main()
