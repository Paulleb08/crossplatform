"""Exécution capturée des outils (wine64, winetricks, hdiutil)."""

import logging
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from . import paths
from .errors import CellierError, CommandFailed

log = logging.getLogger(__name__)


def call(cmd: Sequence[str], env: Mapping[str, str] | None = None, timeout: float = 600) -> str:
    log.debug("exec: %s", shlex.join(cmd))
    try:
        r = subprocess.run(list(cmd), env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, check=False, timeout=timeout)
    except OSError as e:
        raise CommandFailed(f"impossible d'exécuter {cmd[0]} : {e}") from e
    except subprocess.TimeoutExpired as e:
        raise CommandFailed(f"délai dépassé ({timeout:.0f} s) : {shlex.join(cmd)}") from e
    if r.stdout or r.stderr:
        log.debug("sortie de %s:\n%s%s", Path(cmd[0]).name, r.stdout, r.stderr)
    if r.returncode:
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-15:])
        raise CommandFailed(f"échec (code {r.returncode}) : {shlex.join([Path(cmd[0]).name, *cmd[1:]])}\n{tail}".rstrip())
    return r.stdout


def wineserver(env: Mapping[str, str], flag: str) -> None:
    """Best effort : -w attend la fin des processus du préfixe, -k les arrête."""
    try:
        server = paths.wineserver()
        if server:
            subprocess.run([str(server), flag], env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, check=False, timeout=60)
    except (CellierError, OSError, subprocess.TimeoutExpired) as e:
        log.debug("wineserver %s ignoré : %s", flag, e)
