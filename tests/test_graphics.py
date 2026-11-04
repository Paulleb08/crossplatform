from cellier.core import graphics, prefix
from cellier.core.errors import InvalidSetting, MissingComponent

from helpers import FakeWineCase


class GraphicsTest(FakeWineCase):
    def test_env_table(self) -> None:
        b = prefix.Bottle("x")
        for gfx in graphics.BACKENDS:
            for sync in graphics.SYNCS:
                b.graphics, b.sync = gfx, sync
                env = graphics.env_for(b)
                with self.subTest(gfx=gfx, sync=sync):
                    self.assertEqual(env["WINEMSYNC"], "1" if sync == "msync" else "0")
                    self.assertEqual(env["WINEESYNC"], "1" if sync == "esync" else "0")
                    self.assertFalse(env["WINEMSYNC"] == env["WINEESYNC"] == "1")
                    self.assertTrue(env["WINEDLLOVERRIDES"].endswith("=n,b" if gfx == "dxvk" else "=b"))

    def test_switch_roundtrip_restores_dlls(self) -> None:
        b = prefix.create("Jeux")
        dxvk = self.home / "dxvk"
        dxvk.mkdir()
        for d in graphics.DX_DLLS:
            (dxvk / d).write_text("dxvk")
        graphics.configure(b, "dxvk", "esync")
        self.assertEqual((b.system32 / "d3d11.dll").read_text(), "dxvk")
        self.assertEqual(prefix.get("Jeux").graphics, "dxvk")
        graphics.configure(b, "dxvk")  # deux fois de suite : la sauvegarde d'origine est conservée
        graphics.configure(b, "d3dmetal", "msync")
        self.assertEqual((b.system32 / "d3d11.dll").read_text(), "builtin\n")
        self.assertEqual((b.system32 / "dxgi.dll").read_text(), "builtin\n")
        self.assertFalse((b.system32 / "d3d10core.dll").exists())  # absente à l'origine
        self.assertEqual((prefix.get("Jeux").graphics, prefix.get("Jeux").sync), ("d3dmetal", "msync"))

    def test_missing_dxvk(self) -> None:
        b = prefix.create("Jeux")
        with self.assertRaises(MissingComponent):
            graphics.configure(b, "dxvk")
        self.assertEqual(prefix.get("Jeux").graphics, "d3dmetal")

    def test_invalid_values(self) -> None:
        b = prefix.create("Jeux")
        with self.assertRaises(InvalidSetting):
            graphics.configure(b, "opengl")
        with self.assertRaises(InvalidSetting):
            graphics.configure(b, sync="fsync")


class BackupSafetyTest(FakeWineCase):
    def test_failed_switch_keeps_originals_recoverable(self) -> None:
        b = prefix.create("Jeux")
        dxvk = self.home / "dxvk"
        dxvk.mkdir()
        for d in graphics.DX_DLLS:
            (dxvk / d).write_text("dxvk")
        real_copy = graphics.shutil.copy2
        calls = {"n": 0}

        def flaky(src, dst):  # type: ignore[no-untyped-def]
            calls["n"] += 1
            if calls["n"] == 2:
                raise OSError("disque plein")
            return real_copy(src, dst)

        from unittest import mock
        with mock.patch.object(graphics.shutil, "copy2", flaky), self.assertRaises(OSError):
            graphics.configure(b, "dxvk")
        self.assertFalse((b.path / graphics.BACKUP).exists())
        graphics.configure(b, "dxvk")
        graphics.configure(b, "d3dmetal")
        self.assertEqual((b.system32 / "d3d11.dll").read_text(), "builtin\n")
