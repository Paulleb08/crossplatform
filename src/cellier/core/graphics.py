"""Jalon 2 : bascule D3DMetal (GPTK) <-> DXVK (MoltenVK) et MSync / ESync, à chaud."""

import logging
import os
import shutil
from pathlib import Path

from . import paths
from .errors import InvalidSetting, MissingComponent
from .prefix import Bottle

log = logging.getLogger(__name__)
BACKENDS = ("d3dmetal", "dxvk")
SYNCS = ("msync", "esync", "off")
DX_DLLS = ("d3d11.dll", "d3d10core.dll", "dxgi.dll")
BACKUP = "dll-backup"


def env_for(b: Bottle) -> dict[str, str]:
    env = {"WINEMSYNC": "1" if b.sync == "msync" else "0",
           "WINEESYNC": "1" if b.sync == "esync" else "0"}
    if b.graphics == "dxvk":
        env["WINEDLLOVERRIDES"] = "d3d11,d3d10core,dxgi=n,b"  # DLL DXVK copiées dans system32
    else:
        env["WINEDLLOVERRIDES"] = "d3d11,d3d10core,dxgi,d3d12=b"  # DLL intégrées = D3DMetal sous GPTK
    return env


def dxvk_dir() -> Path:
    value = os.environ.get("CELLIER_DXVK")
    return Path(value).expanduser() if value else paths.home() / "Components" / "dxvk" / "x64"


def d3dmetal_available(wine: Path) -> bool:
    return (wine.resolve().parent.parent / "lib" / "external" / "D3DMetal.framework").exists()


def _install_dxvk(b: Bottle) -> None:
    src = dxvk_dir()
    missing = [d for d in DX_DLLS if not (src / d).is_file()]
    if missing:
        raise MissingComponent(
            f"DLL DXVK absentes dans {src} : {', '.join(missing)}. Copiez-y les DLL x64 de DXVK-macOS "
            "(github.com/Gcenx/DXVK-macOS) ou indiquez leur dossier avec CELLIER_DXVK.")
    backup = b.path / BACKUP
    if not backup.exists():  # déjà sous DXVK : ne pas sauvegarder les DLL DXVK comme originales
        tmp = b.path / f"{BACKUP}.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir()
        for d in DX_DLLS:
            if (b.system32 / d).exists():
                shutil.copy2(b.system32 / d, tmp / d)
        tmp.rename(backup)  # sauvegarde complète ou absente, jamais partielle
    for d in DX_DLLS:
        shutil.copy2(src / d, b.system32 / d)


def _restore_builtin(b: Bottle) -> None:
    backup = b.path / BACKUP
    if not backup.is_dir():
        return
    for d in DX_DLLS:
        if (backup / d).exists():
            shutil.copy2(backup / d, b.system32 / d)
        else:
            (b.system32 / d).unlink(missing_ok=True)  # ajoutée par DXVK, absente à l'origine
    shutil.rmtree(backup)


def configure(b: Bottle, graphics: str | None = None, sync: str | None = None) -> Bottle:
    if graphics is not None and graphics not in BACKENDS:
        raise InvalidSetting(f"moteur graphique inconnu : {graphics} (choix : {', '.join(BACKENDS)})")
    if sync is not None and sync not in SYNCS:
        raise InvalidSetting(f"synchronisation inconnue : {sync} (choix : {', '.join(SYNCS)})")
    if graphics == "dxvk":
        _install_dxvk(b)
    elif graphics == "d3dmetal":
        _restore_builtin(b)
        if not d3dmetal_available(paths.wine()):
            log.warning("D3DMetal non détecté à côté de Wine : DirectX 12 peut ne pas fonctionner. "
                        "Utilisez le Wine du Game Porting Toolkit.")
    if graphics is not None:
        b.graphics = graphics
    if sync is not None:
        b.sync = sync
    b.save()
    log.info("%s : graphismes=%s, synchronisation=%s", b.name, b.graphics, b.sync)
    return b
