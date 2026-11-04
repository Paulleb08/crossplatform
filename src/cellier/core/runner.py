"""Jalon 3 : lancement des programmes Windows avec journal par exécution."""

import logging
import re
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from . import graphics, media, paths
from .errors import CellierError, CommandFailed
from .prefix import Bottle, base_env

log = logging.getLogger(__name__)
WIN_PATH = re.compile(r"^[A-Za-z]:\\")


def _wineserver(env: Mapping[str, str], flag: str) -> None:
    server = paths.wineserver()
    if server:
        subprocess.run([str(server), flag], env=env, stdin=subprocess.DEVNULL,
                       capture_output=True, check=False)


def _windows_cwd(b: Bottle, target: str) -> Path:
    if target[0].lower() == "c":
        d = b.prefix / "drive_c" / Path(*target[3:].split("\\")).parent
        if d.is_dir():
            return d
    return b.prefix / "drive_c"


def launch(b: Bottle, target: str, args: Sequence[str] = ()) -> int:
    wine = str(paths.wine())
    local = Path(target).expanduser()
    if local.is_file():
        local = local.resolve()
        kind = media.detect(local)
        if kind == "iso":
            with media.mount(local) as point:
                return launch(b, str(media.find_installer(point)), args)
        cmd = [wine, "msiexec", "/i", str(local)] if kind == "msi" else [wine, str(local)]
        cwd = local.parent
    elif WIN_PATH.match(target):
        cmd, cwd = [wine, target], _windows_cwd(b, target)
    else:
        raise CellierError(f"fichier introuvable : {target}")
    cmd += list(args)

    gfx = graphics.env_for(b)
    env = {**base_env(b), **gfx}
    log_path = paths.logs_dir() / b.name / f"{datetime.now():%Y%m%d-%H%M%S-%f}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log.info("Lancement dans %r (%s, %s)… journal : %s", b.name, b.graphics, b.sync, log_path)
    with log_path.open("w", encoding="utf-8") as fh:
        fh.write(f"# {shlex.join(cmd)}\n# cwd={cwd}\n# {gfx}\n")
        fh.flush()
        try:
            proc = subprocess.Popen(cmd, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                                    stdout=fh, stderr=subprocess.STDOUT)
        except OSError as e:
            raise CommandFailed(f"impossible de lancer Wine : {e}") from e
        try:
            code = proc.wait()
            _wineserver(env, "-w")  # attend les processus enfants (installeurs, lanceurs)
        except KeyboardInterrupt:
            _wineserver(env, "-k")
            proc.wait()
            code = 130
    if code:
        log.warning("Terminé avec le code %d. Détails : %s", code, log_path)
    return code
