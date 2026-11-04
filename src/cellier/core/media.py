"""Jalon 3 : détection .exe / .msi / .iso et montage des ISO avec hdiutil."""

import logging
import plistlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from . import process
from .errors import CellierError, MountFailed, UnsupportedFile

log = logging.getLogger(__name__)
OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
ISO_MAGICS = (b"CD001", b"BEA01", b"NSR02", b"NSR03")  # ISO 9660 / UDF


def detect(path: Path) -> str:
    with path.open("rb") as f:
        head = f.read(8)
        f.seek(32769)
        iso = f.read(5)
    if head[:2] == b"MZ":
        return "exe"
    if head == OLE_MAGIC:
        return "msi"
    if iso in ISO_MAGICS:
        return "iso"
    raise UnsupportedFile(f"{path.name} n'est ni un .exe, ni un .msi, ni une image ISO")


@contextmanager
def mount(iso: Path) -> Iterator[Path]:
    try:
        out = process.call(["hdiutil", "attach", "-nobrowse", "-readonly", "-plist", str(iso)])
        entities = plistlib.loads(out.encode())["system-entities"]
        point = next(Path(e["mount-point"]) for e in entities if "mount-point" in e)
    except (CellierError, plistlib.InvalidFileException, KeyError, StopIteration) as e:
        raise MountFailed(f"montage de {iso.name} impossible : {e}") from e
    log.info("Image montée sur %s", point)
    try:
        yield point
    finally:
        try:
            process.call(["hdiutil", "detach", str(point)])
        except CellierError as e:
            log.warning("démontage de %s impossible : %s", point, e)


def find_installer(root: Path) -> Path:
    files = {p.name.lower(): p for p in root.iterdir() if p.is_file()}
    if "autorun.inf" in files:
        for line in files["autorun.inf"].read_text(errors="ignore").splitlines():
            key, _, value = line.partition("=")
            if key.strip().lower() == "open" and value.strip():
                cand = root / value.strip().split()[0].replace("\\", "/")
                if cand.is_file():
                    return cand
    for name in ("setup.exe", "install.exe"):
        if name in files:
            return files[name]
    exes = sorted(p for n, p in files.items() if n.endswith(".exe"))
    if exes:
        return exes[0]
    raise MountFailed(f"aucun installateur trouvé dans {root}")
