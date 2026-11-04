"""Jalon 1 : runtimes Windows courants via Winetricks."""

import logging
from collections.abc import Sequence

from . import paths, process
from .prefix import Bottle, base_env

log = logging.getLogger(__name__)
# vcrun2022 couvre Visual C++ 2015 à 2022 (même redistribuable).
DEFAULT_VERBS = ("vcrun2022", "corefonts", "d3dcompiler_47")


def install(b: Bottle, verbs: Sequence[str] = DEFAULT_VERBS) -> None:
    tricks = str(paths.winetricks())
    env = {**base_env(b), "WINE": str(paths.wine())}
    server = paths.wineserver()
    if server:
        env["WINESERVER"] = str(server)
    log.info("Installation des composants Windows : %s (plusieurs minutes)…", ", ".join(verbs))
    process.call([tricks, "-q", *verbs], env)
