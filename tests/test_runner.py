from pathlib import Path
from unittest import mock

from cellier.core import graphics, media, paths, prefix, runner
from cellier.core.errors import CellierError

from helpers import FakeWineCase


class RunnerTest(FakeWineCase):
    def setUp(self) -> None:
        super().setUp()
        self.b = prefix.create("Jeux")
        (self.home / "calls.log").unlink()
        self.games = self.home / "Mes Jeux"
        self.games.mkdir()

    def test_exe_with_spaces_env_and_log(self) -> None:
        exe = self.games / "Mon Jeu.exe"
        exe.write_bytes(b"MZ" + b"\0" * 100)
        self.assertEqual(runner.launch(self.b, str(exe), ["-fullscreen"]), 0)
        log = self.calls()
        self.assertIn(f"ARG:{exe}\nARG:-fullscreen", log)
        self.assertIn(f"|win64|1|0|d3d11,d3d10core,dxgi,d3d12=b|{self.games}", log)
        logs = list((paths.logs_dir() / "Jeux").glob("*.log"))
        self.assertEqual(len(logs), 1)
        self.assertIn("Mon Jeu.exe", logs[0].read_text())

    def test_exit_code_propagated(self) -> None:
        exe = self.games / "a.exe"
        exe.write_bytes(b"MZ")
        self.fail_next()
        self.assertEqual(runner.launch(self.b, str(exe)), 3)
        log = next((paths.logs_dir() / "Jeux").glob("*.log")).read_text()
        self.assertIn("boom stderr", log)

    def test_msi_uses_msiexec(self) -> None:
        msi = self.games / "a.msi"
        msi.write_bytes(media.OLE_MAGIC)
        runner.launch(self.b, str(msi))
        self.assertIn(f"ARG:msiexec\nARG:/i\nARG:{msi}", self.calls())

    def test_windows_path_runs_in_game_dir(self) -> None:
        game_dir = self.b.prefix / "drive_c" / "Games" / "X"
        game_dir.mkdir(parents=True)
        self.b.sync = "esync"
        runner.launch(self.b, "C:\\Games\\X\\x.exe")
        self.assertIn(f"|0|1|d3d11,d3d10core,dxgi,d3d12=b|{game_dir}\nARG:C:\\Games\\X\\x.exe", self.calls())

    def test_iso_mounts_and_runs_installer(self) -> None:
        iso = self.games / "g.iso"
        data = bytearray(40000)
        data[32769:32774] = b"CD001"
        iso.write_bytes(bytes(data))
        vol = self.home / "vol"
        vol.mkdir()
        (vol / "setup.exe").write_bytes(b"MZ")
        with mock.patch.object(media, "mount") as m:
            m.return_value.__enter__.return_value = vol
            runner.launch(self.b, str(iso))
        self.assertIn(f"ARG:{vol / 'setup.exe'}", self.calls())

    def test_missing_file(self) -> None:
        with self.assertRaises(CellierError):
            runner.launch(self.b, "/nulle/part.exe")
