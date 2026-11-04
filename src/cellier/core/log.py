"""Journalisation : console (INFO, ou DEBUG avec -v) et fichier cellier.log (DEBUG)."""

import logging
import sys

from . import paths


def setup(verbose: bool = False) -> None:
    root = logging.getLogger("cellier")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(console)
    try:
        paths.logs_dir().mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(paths.logs_dir() / "cellier.log", encoding="utf-8")
    except OSError as e:
        root.warning("journal fichier indisponible : %s", e)
        return
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(fh)
