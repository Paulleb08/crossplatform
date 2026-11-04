"""Exécution capturée des outils (wine64, winetricks, hdiutil)."""

import logging
import shlex
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from .errors import CommandFailed

log = logging.getLogger(__name__)


def call(cmd: Sequence[str], env: Mapping[str, str] | None = None) -> str:
    log.debug("exec: %s", shlex.join(cmd))
    try:
        r = subprocess.run(list(cmd), env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, check=False)
    except OSError as e:
        raise CommandFailed(f"impossible d'exécuter {cmd[0]} : {e}") from e
    if r.stdout or r.stderr:
        log.debug("sortie de %s:\n%s%s", Path(cmd[0]).name, r.stdout, r.stderr)
    if r.returncode:
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-15:])
        raise CommandFailed(f"{Path(cmd[0]).name} {cmd[1] if len(cmd) > 1 else ''} a échoué (code {r.returncode})\n{tail}".rstrip())
    return r.stdout
