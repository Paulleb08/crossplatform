import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cellier.core import media
from cellier.core.errors import CommandFailed, MountFailed, UnsupportedFile


def make(path: Path, head: bytes, iso: bool = False) -> Path:
    data = bytearray(head.ljust(40000, b"\0"))
    if iso:
        data[32769:32774] = b"CD001"
    path.write_bytes(bytes(data))
    return path


class MediaTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_detect_by_signature(self) -> None:
        self.assertEqual(media.detect(make(self.dir / "a.exe", b"MZ")), "exe")
        self.assertEqual(media.detect(make(self.dir / "renamed.bin", b"MZ")), "exe")
        self.assertEqual(media.detect(make(self.dir / "a.msi", media.OLE_MAGIC)), "msi")
        self.assertEqual(media.detect(make(self.dir / "a.iso", b"", iso=True)), "iso")
        with self.assertRaises(UnsupportedFile):
            media.detect(make(self.dir / "fake.exe", b"PK"))

    def test_find_installer(self) -> None:
        (self.dir / "Setup.exe").write_text("")
        self.assertEqual(media.find_installer(self.dir).name, "Setup.exe")
        (self.dir / "bin").mkdir()
        (self.dir / "bin" / "go.exe").write_text("")
        (self.dir / "AUTORUN.INF").write_text("[autorun]\nopen=bin\\go.exe /x\n")
        self.assertEqual(media.find_installer(self.dir), self.dir / "bin" / "go.exe")
        (self.dir / "vide").mkdir()
        with self.assertRaises(MountFailed):
            media.find_installer(self.dir / "vide")

    def test_mount_detaches_even_on_error(self) -> None:
        out = plistlib.dumps({"system-entities": [{"dev-entry": "/dev/disk4"},
                                                  {"mount-point": "/Volumes/GAME"}]}).decode()
        with mock.patch.object(media.process, "call", side_effect=[out, ""]) as call:
            with self.assertRaises(RuntimeError):
                with media.mount(self.dir / "g.iso") as point:
                    self.assertEqual(point, Path("/Volumes/GAME"))
                    raise RuntimeError
        self.assertEqual(call.call_args_list[1].args[0], ["hdiutil", "detach", "/Volumes/GAME"])

    def test_mount_failure(self) -> None:
        with mock.patch.object(media.process, "call", side_effect=CommandFailed("hdiutil: no")):
            with self.assertRaises(MountFailed):
                with media.mount(self.dir / "g.iso"):
                    pass
