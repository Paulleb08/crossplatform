import io
import json
import os
import plistlib
from contextlib import redirect_stderr, redirect_stdout

from cellier.cli import main
from cellier.core import paths

from helpers import FakeWineCase


class CliTest(FakeWineCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_full_cycle(self) -> None:
        self.assertEqual(self.run_cli("create", "Jeux")[0], 0)
        self.assertIn("ARG:vcrun2022", self.calls())
        code, out, _ = self.run_cli("list", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)[0]["name"], "Jeux")
        code, out, _ = self.run_cli("config", "Jeux", "--sync", "esync")
        self.assertIn("synchronisation=esync", out)
        code, _, err = self.run_cli("delete", "Jeux")
        self.assertEqual(code, 1)
        self.assertIn("--yes", err)
        self.assertEqual(self.run_cli("delete", "Jeux", "--yes")[0], 0)
        self.assertIn("Aucune bouteille", self.run_cli("list")[1])

    def test_error_is_readable(self) -> None:
        code, _, err = self.run_cli("run", "Inconnue", "x.exe")
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("erreur : bouteille 'Inconnue' introuvable"))
        self.assertNotIn("Traceback", err)

    def test_shortcut_app(self) -> None:
        self.run_cli("create", "Jeux", "--no-deps")
        code, _, _ = self.run_cli("shortcut", "Jeux", "C:\\Games\\X\\x.exe", "--name", "Mon Jeu")
        self.assertEqual(code, 0)
        app = paths.apps_dir() / "Mon Jeu.app"
        info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
        self.assertEqual(info["CFBundleExecutable"], "launch")
        launcher = app / "Contents" / "MacOS" / "launch"
        self.assertTrue(os.access(launcher, os.X_OK))
        self.assertIn("-m cellier run Jeux 'C:\\Games\\X\\x.exe'", launcher.read_text())
