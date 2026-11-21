import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import downloads


class Downloads(unittest.TestCase):
    def test_asset_high_water_marks_and_failed_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            catalog = root / "list.json"
            def listing(repo):
                catalog.write_text(json.dumps({"plugins": [{"id": "fern",
                    "link": f"https://github.com/{repo}/tree/v1"}]}))
            def sample(assets):
                releases = [{"id": 1, "draft": False}]
                files = [dict(id=id, name="loam-fern.tar", state="uploaded", download_count=n)
                         for id, n in assets]
                with patch.object(downloads, "api", side_effect=[releases, files]):
                    downloads.collect(root)
                return json.loads((root / "stats.json").read_text())["plugins"]["fern"]["downloads"]
            listing("maker/fern")
            self.assertEqual(sample([(3, 10)]), 10)
            self.assertEqual(sample([(3, 8)]), 10)
            self.assertEqual(sample([]), 10)
            listing("maker/renamed")
            self.assertEqual(sample([(4, 2)]), 12)
            past = (root / "stats.json").read_bytes()
            with patch.object(downloads, "api", side_effect=OSError("unavailable")):
                with self.assertRaises(OSError):
                    downloads.collect(root)
            self.assertEqual((root / "stats.json").read_bytes(), past)


if __name__ == "__main__":
    unittest.main()
