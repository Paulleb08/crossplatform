"""Prérequis (Rosetta, Homebrew, Wine/GPTK, Winetricks) : détection et script d'installation."""

from pathlib import Path

from . import paths
from .errors import WineNotFound

SCRIPT = """#!/bin/bash
# Généré par Cellier : installe Rosetta 2, Homebrew, Wine (Game Porting Toolkit) et Winetricks.
set -e
echo "== Rosetta 2"; softwareupdate --install-rosetta --agree-to-license || true
if ! command -v brew >/dev/null && [ ! -x /opt/homebrew/bin/brew ]; then
  echo "== Homebrew"; /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
eval "$(/opt/homebrew/bin/brew shellenv)"
echo "== Wine + D3DMetal"; brew install --cask gcenx/wine/game-porting-toolkit
# Homebrew a retiré --no-quarantine : on lève la quarantaine Gatekeeper sur l'app Wine installée.
xattr -dr com.apple.quarantine /Applications/*Wine*.app "/Applications/Game Porting Toolkit.app" 2>/dev/null || true
echo "== Winetricks"; brew install winetricks
echo; echo "Terminé. Revenez dans Cellier et cliquez sur « Vérifier à nouveau »."
"""


def status() -> dict[str, Path | None]:
    found: dict[str, Path | None] = {}
    for name, finder in (("wine", paths.wine), ("winetricks", paths.winetricks)):
        try:
            found[name] = finder()
        except WineNotFound:
            found[name] = None
    return found


def write_script() -> Path:
    f = paths.home() / "installer-prerequis.command"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(SCRIPT, encoding="utf-8")
    f.chmod(0o755)
    return f
