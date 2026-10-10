from pathlib import Path
import unittest


class ExampleTest(unittest.TestCase):
    def test_example_value_is_ready(self):
        value = Path("src/example.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(value, "ready")


if __name__ == "__main__":
    unittest.main()
