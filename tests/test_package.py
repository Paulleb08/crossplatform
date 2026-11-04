import unittest

import cellier
from cellier.cli import main


class PackageTest(unittest.TestCase):
    def test_version(self) -> None:
        self.assertEqual(cellier.__version__, "0.0.1")

    def test_cli_stub_fails_cleanly(self) -> None:
        self.assertEqual(main([]), 1)


if __name__ == "__main__":
    unittest.main()
