"""Jalon 4 : raccourcis .app (double-clic dans le Finder ou le Dock)."""

import logging
import plistlib
import re
import shlex
import sys
from pathlib import Path, PureWindowsPath

from . import paths
from .errors import InvalidName
from .prefix import Bottle

log = logging.getLogger(__name__)
SRC_ROOT = Path(__file__).resolve().parents[2]


def _cellier_cmd() -> str:
    # Dans Cellier.app (PyInstaller), sys.executable est le binaire de l'app : il accepte les sous-commandes.
    if getattr(sys, "frozen", False):
        return shlex.quote(sys.executable)
    return f"{shlex.quote(sys.executable)} -m cellier"


def to_windows_path(b: Bottle, local: Path) -> str:
    """Chemin Mac d'un programme installé dans drive_c -> chemin Windows C:\\…"""
    rel = local.resolve().relative_to((b.prefix / "drive_c").resolve())  # ValueError si hors du disque C:
    return str(PureWindowsPath("C:/", *rel.parts))


def create_app(b: Bottle, target: str, name: str) -> Path:
    if not re.fullmatch(r"[^/:\x00]{1,64}", name) or name.startswith("."):
        raise InvalidName(f"nom de raccourci invalide : {name!r}")
    app = paths.apps_dir() / f"{name}.app"
    macos = app / "Contents" / "MacOS"
    macos.mkdir(parents=True, exist_ok=True)
    launcher = macos / "launch"
    launcher.write_text(
        "#!/bin/sh\n"
        f"# Généré par Cellier pour la bouteille {b.name}\n"
        f"export PYTHONPATH={shlex.quote(str(SRC_ROOT))}${{PYTHONPATH:+:$PYTHONPATH}}\n"
        f"exec {_cellier_cmd()} run {shlex.quote(b.name)} {shlex.quote(target)} \"$@\"\n",
        encoding="utf-8")
    launcher.chmod(0o755)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", f"{b.name}-{name}").strip("-").lower()
    with (app / "Contents" / "Info.plist").open("wb") as f:
        plistlib.dump({
            "CFBundleName": name, "CFBundleDisplayName": name,
            "CFBundleIdentifier": f"org.cellier.{slug}", "CFBundleExecutable": "launch",
            "CFBundlePackageType": "APPL", "CFBundleVersion": "1", "LSMinimumSystemVersion": "14.0",
        }, f)
    log.info("Raccourci créé : %s", app)
    return app
