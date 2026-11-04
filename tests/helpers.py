"""Faux Wine : scripts shell qui journalisent leurs appels. Wine n'est jamais lancé pour de vrai."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

FAKE_WINE = r"""#!/bin/sh
{
  echo "CALL|$WINEPREFIX|$WINEARCH|$WINEMSYNC|$WINEESYNC|$WINEDLLOVERRIDES|$(pwd)"
  for a in "$@"; do echo "ARG:$a"; done
} >> "$CELLIER_HOME/calls.log"
if [ -e "$CELLIER_HOME/fail" ]; then echo "boom stderr" >&2; exit 3; fi
if [ "$1" = wineboot ]; then
  s="$WINEPREFIX/drive_c/windows/system32"; mkdir -p "$s"
  for d in d3d11 dxgi; do echo builtin > "$s/$d.dll"; done
fi
exit 0
"""


class FakeWineCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        bindir = self.home / "bin"
        bindir.mkdir()
        for tool in ("wine64", "wineserver", "winetricks"):
            p = bindir / tool
            p.write_text(FAKE_WINE)
            p.chmod(0o755)
        patcher = mock.patch.dict(os.environ, {
            "CELLIER_HOME": str(self.home),
            "CELLIER_WINE": str(bindir / "wine64"),
            "CELLIER_WINETRICKS": str(bindir / "winetricks"),
            "CELLIER_DXVK": str(self.home / "dxvk"),
        })
        patcher.start()
        self.addCleanup(patcher.stop)

    def calls(self) -> str:
        log = self.home / "calls.log"
        return log.read_text() if log.exists() else ""

    def fail_next(self) -> None:
        (self.home / "fail").touch()
