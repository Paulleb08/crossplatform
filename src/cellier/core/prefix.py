"""Jalon 1 : bouteilles = préfixes WINEPREFIX Windows 10 64-bit isolés."""

import json
import logging
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import paths, process
from .errors import BottleExists, BottleNotFound, CellierError, InvalidName

log = logging.getLogger(__name__)
CONFIG = "bottle.json"
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,63}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Bottle:
    name: str
    graphics: str = "d3dmetal"
    sync: str = "msync"
    created: str = field(default_factory=_now)

    @property
    def path(self) -> Path:
        return paths.bottles_dir() / self.name

    @property
    def prefix(self) -> Path:
        return self.path / "prefix"

    @property
    def system32(self) -> Path:
        return self.prefix / "drive_c" / "windows" / "system32"

    def save(self) -> None:
        (self.path / CONFIG).write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")

    def to_dict(self) -> dict[str, str]:
        return {**asdict(self), "path": str(self.path)}


def validate_name(name: str) -> None:
    if not NAME_RE.fullmatch(name) or ".." in name:
        raise InvalidName(f"nom invalide : {name!r} (lettres, chiffres, espace, . _ -, 64 max)")


LEAKY_VARS = ("WINELOADER", "WINEDLLOVERRIDES", "WINEESYNC", "WINEMSYNC", "WINESERVER")


def base_env(b: Bottle) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in LEAKY_VARS}  # réglages du shell ≠ réglages de la bouteille
    return {**env, "WINEPREFIX": str(b.prefix), "WINEARCH": "win64",
            "WINEDEBUG": os.environ.get("WINEDEBUG", "-all")}


def create(name: str) -> Bottle:
    validate_name(name)
    b = Bottle(name)
    if b.path.exists():
        raise BottleExists(f"la bouteille {name!r} existe déjà")
    wine = str(paths.wine())
    try:
        b.path.mkdir(parents=True)
    except FileExistsError as e:
        raise BottleExists(f"la bouteille {name!r} existe déjà") from e
    # Sans mscoree/mshtml, wineboot ne propose pas de télécharger Mono/Gecko dans une fenêtre bloquante.
    env = {**base_env(b), "WINEDLLOVERRIDES": "mscoree,mshtml="}
    try:
        log.info("Initialisation du préfixe Windows 64-bit…")
        process.call([wine, "wineboot", "--init"], env, timeout=300)
        process.wineserver(env, "-w")
        log.info("Réglage sur Windows 10…")
        process.call([wine, "winecfg", "-v", "win10"], env, timeout=120)
        process.wineserver(env, "-w")
        b.save()
    except BaseException:
        process.wineserver(env, "-k")  # sinon wineserver réécrit dans le dossier pendant sa suppression
        shutil.rmtree(b.path, ignore_errors=True)  # pas de bouteille à moitié créée
        raise
    log.info("Bouteille %r créée : %s", name, b.path)
    return b


def _load(cfg: Path) -> Bottle:
    data = json.loads(cfg.read_text(encoding="utf-8"))
    fields = {k: str(data[k]) for k in ("graphics", "sync", "created") if k in data}
    return Bottle(name=cfg.parent.name, **fields)  # le dossier fait foi : un JSON copié ou édité ne doit pas viser une autre bouteille


def get(name: str) -> Bottle:
    validate_name(name)
    cfg = paths.bottles_dir() / name / CONFIG
    if not cfg.is_file():
        raise BottleNotFound(f"bouteille {name!r} introuvable (voir : cellier list)")
    try:
        return _load(cfg)
    except (ValueError, TypeError, AttributeError) as e:
        raise CellierError(f"configuration illisible : {cfg} ({e})") from e


def list_bottles() -> list[Bottle]:
    root = paths.bottles_dir()
    if not root.is_dir():
        return []
    out = []
    for cfg in sorted(root.glob(f"*/{CONFIG}")):
        try:
            out.append(_load(cfg))
        except (ValueError, TypeError, AttributeError) as e:
            log.warning("configuration illisible ignorée : %s (%s)", cfg, e)
    return out


def delete(name: str) -> None:
    b = get(name)
    target, root = b.path.resolve(), paths.bottles_dir().resolve()
    if target.parent != root:
        raise CellierError(f"refus de supprimer {target} : hors de {root}")
    process.wineserver(base_env(b), "-k")
    shutil.rmtree(target)
    log.info("Bouteille %r supprimée", name)
