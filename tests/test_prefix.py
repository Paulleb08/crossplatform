import json

from cellier.core import deps, paths, prefix
from cellier.core.errors import BottleExists, BottleNotFound, CommandFailed, InvalidName, WineNotFound

from helpers import FakeWineCase


class PrefixTest(FakeWineCase):
    def test_create_initialises_win10_64(self) -> None:
        b = prefix.create("Jeux")
        data = json.loads((b.path / "bottle.json").read_text())
        self.assertEqual((data["name"], data["graphics"], data["sync"]), ("Jeux", "d3dmetal", "msync"))
        log = self.calls()
        self.assertIn(f"CALL|{b.prefix}|win64|", log)
        self.assertIn("ARG:wineboot\nARG:--init", log)
        self.assertIn("ARG:winecfg\nARG:-v\nARG:win10", log)

    def test_duplicate_refused(self) -> None:
        prefix.create("Jeux")
        with self.assertRaises(BottleExists):
            prefix.create("Jeux")

    def test_invalid_names(self) -> None:
        for bad in ("", "../x", "a/b", ".cache", "x" * 65, "a..b"):
            with self.subTest(bad=bad), self.assertRaises(InvalidName):
                prefix.create(bad)

    def test_failure_cleans_up(self) -> None:
        self.fail_next()
        with self.assertRaises(CommandFailed) as ctx:
            prefix.create("Jeux")
        self.assertIn("boom stderr", str(ctx.exception))
        self.assertFalse((paths.bottles_dir() / "Jeux").exists())

    def test_list_ignores_foreign_dirs(self) -> None:
        prefix.create("B")
        prefix.create("A")
        (paths.bottles_dir() / "pas-une-bouteille").mkdir()
        self.assertEqual([b.name for b in prefix.list_bottles()], ["A", "B"])

    def test_delete(self) -> None:
        b = prefix.create("Jeux")
        prefix.delete("Jeux")
        self.assertFalse(b.path.exists())
        with self.assertRaises(BottleNotFound):
            prefix.get("Jeux")

    def test_wine_override_must_be_executable(self) -> None:
        import os
        os.environ["CELLIER_WINE"] = str(self.home / "nope")
        with self.assertRaises(WineNotFound):
            prefix.create("Jeux")

    def test_deps_use_winetricks_quiet(self) -> None:
        b = prefix.create("Jeux")
        deps.install(b)
        self.assertIn("ARG:-q\nARG:vcrun2022\nARG:corefonts\nARG:d3dcompiler_47", self.calls())
