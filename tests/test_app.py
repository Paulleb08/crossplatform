import os
import sys
from pathlib import Path
from unittest import mock

from cellier import app
from cellier.core import paths, prefix, prereqs, shortcuts

from helpers import FakeWineCase


class AppEntryTest(FakeWineCase):
    def test_args_go_to_cli_and_finder_psn_is_ignored(self) -> None:
        with mock.patch.object(sys, "argv", ["Cellier", "-psn_0_123", "list"]), \
                mock.patch.object(app.cli, "main", return_value=0) as cli_main, \
                self.assertRaises(SystemExit) as ctx:
            app.main()
        cli_main.assert_called_once_with(["list"])
        self.assertEqual(ctx.exception.code, 0)

    def test_prereq_status_and_script(self) -> None:
        self.assertEqual(prereqs.status()["wine"], Path(os.environ["CELLIER_WINE"]))
        os.environ["CELLIER_WINETRICKS"] = str(self.home / "absent")
        self.assertIsNone(prereqs.status()["winetricks"])
        script = prereqs.write_script()
        self.assertTrue(os.access(script, os.X_OK))
        self.assertIn("brew install winetricks", script.read_text())

    def test_to_windows_path(self) -> None:
        b = prefix.create("Jeux")
        exe = b.prefix / "drive_c" / "Games" / "Mon Jeu" / "jeu.exe"
        exe.parent.mkdir(parents=True)
        exe.write_text("")
        self.assertEqual(shortcuts.to_windows_path(b, exe), "C:\\Games\\Mon Jeu\\jeu.exe")
        with self.assertRaises(ValueError):
            shortcuts.to_windows_path(b, self.home / "ailleurs.exe")

    def test_frozen_shortcut_calls_app_binary(self) -> None:
        b = prefix.create("Jeux")
        with mock.patch.object(sys, "frozen", True, create=True), \
                mock.patch.object(sys, "executable", "/Applications/Cellier.app/Contents/MacOS/Cellier"):
            app_dir = shortcuts.create_app(b, "C:\\x.exe", "X")
        text = (app_dir / "Contents" / "MacOS" / "launch").read_text()
        self.assertIn("exec /Applications/Cellier.app/Contents/MacOS/Cellier run Jeux", text)
        self.assertEqual(app_dir.parent, paths.apps_dir())
