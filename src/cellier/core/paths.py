"""Emplacements sur le Mac et détection des outils Wine."""

import os
import shutil
from pathlib import Path

from .errors import WineNotFound

INSTALL_HINT = "Installez-le : brew install --cask gcenx/wine/game-porting-toolkit"
SEARCH_DIRS = [
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
    Path("/Applications/Game Porting Toolkit.app/Contents/Resources/wine/bin"),
    Path("/Applications/Wine Crossover.app/Contents/Resources/wine/bin"),
    Path("/Applications/Wine Stable.app/Contents/Resources/wine/bin"),
]


def _override() -> Path | None:
    value = os.environ.get("CELLIER_HOME")
    return Path(value).expanduser() if value else None


def home() -> Path:
    return _override() or Path.home() / "Library" / "Application Support" / "Cellier"


def bottles_dir() -> Path:
    return home() / "Bottles"


def logs_dir() -> Path:
    root = _override()
    return root / "Logs" if root else Path.home() / "Library" / "Logs" / "Cellier"


def apps_dir() -> Path:
    root = _override()
    return root / "Applications" if root else Path.home() / "Applications" / "Cellier"


def _executable(p: Path) -> bool:
    return p.is_file() and os.access(p, os.X_OK)


def find_tool(names: tuple[str, ...], env_var: str, hint: str) -> Path:
    override = os.environ.get(env_var)
    if override:
        p = Path(override).expanduser()
        if _executable(p):
            return p
        raise WineNotFound(f"{env_var}={override} n'est pas un exécutable.")
    for name in names:
        found = shutil.which(name)
        if found:
            return Path(found)
        for d in SEARCH_DIRS:
            if _executable(d / name):
                return d / name
    raise WineNotFound(f"{names[0]} introuvable. {hint}")


def wine() -> Path:
    # Wine >= 9 en mode WoW64 ne fournit parfois que `wine`.
    return find_tool(("wine64", "wine"), "CELLIER_WINE", INSTALL_HINT)


def wineserver() -> Path | None:
    beside = wine().parent / "wineserver"
    if _executable(beside):
        return beside
    found = shutil.which("wineserver")
    return Path(found) if found else None


def winetricks() -> Path:
    return find_tool(("winetricks",), "CELLIER_WINETRICKS", "Installez-le : brew install winetricks")
