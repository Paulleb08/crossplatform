"""Jalon 4 : CLI `cellier`. Sortie --json = contrat pour une future interface SwiftUI."""

import argparse
import json
import logging
import shlex
import sys
from collections.abc import Callable

from cellier import __version__
from cellier.core import deps, graphics, log as clog, prefix, runner, shortcuts
from cellier.core.errors import CellierError

log = logging.getLogger("cellier.cli")


def _create(a: argparse.Namespace) -> int:
    b = prefix.create(a.name)
    graphics.configure(b, a.graphics, a.sync)
    if not a.no_deps:
        try:
            deps.install(b)
        except CellierError as e:
            raise CellierError(f"bouteille {b.name!r} créée, mais les composants Windows ont échoué. "
                               f"Réessayez : WINEPREFIX={shlex.quote(str(b.prefix))} winetricks -q "
                               f"{' '.join(deps.DEFAULT_VERBS)}\n{e}") from e
    print(f"Prête. Lancez un programme : cellier run {b.name!r} ~/Downloads/setup.exe")
    return 0


def _list(a: argparse.Namespace) -> int:
    bottles = prefix.list_bottles()
    if a.json:
        print(json.dumps([b.to_dict() for b in bottles], indent=2, ensure_ascii=False))
    elif not bottles:
        print("Aucune bouteille. Créez-en une : cellier create MesJeux")
    else:
        print(f"{'NOM':<24}{'GRAPHISMES':<12}{'SYNC':<8}CRÉÉE")
        for b in bottles:
            print(f"{b.name:<24}{b.graphics:<12}{b.sync:<8}{b.created[:10]}")
    return 0


def _run(a: argparse.Namespace) -> int:
    args = a.args[1:] if a.args[:1] == ["--"] else a.args
    return runner.launch(prefix.get(a.name), a.target, args)


def _config(a: argparse.Namespace) -> int:
    b = prefix.get(a.name)
    if a.graphics or a.sync:
        b = graphics.configure(b, a.graphics, a.sync)
    print(json.dumps(b.to_dict(), indent=2, ensure_ascii=False) if a.json
          else f"{b.name} : graphismes={b.graphics}, synchronisation={b.sync}")
    return 0


def _delete(a: argparse.Namespace) -> int:
    if not a.yes:
        print(f"Suppression définitive de {a.name!r} et de tout son contenu. "
              "Relancez avec --yes pour confirmer.", file=sys.stderr)
        return 1
    prefix.delete(a.name)
    return 0


def _shortcut(a: argparse.Namespace) -> int:
    app = shortcuts.create_app(prefix.get(a.name), a.target, a.label or a.name)
    print(f"Raccourci prêt : {app} (glissez-le dans le Dock)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cellier", description="Programmes Windows sur Mac Apple Silicon.")
    p.add_argument("--version", action="version", version=f"cellier {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", help="afficher les détails")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMANDE")

    def add(name: str, fn: Callable[[argparse.Namespace], int], help: str) -> argparse.ArgumentParser:
        s = sub.add_parser(name, help=help, description=help)
        s.set_defaults(fn=fn)
        return s

    s = add("create", _create, "créer une bouteille Windows 10 64-bit")
    s.add_argument("name")
    s.add_argument("--graphics", choices=graphics.BACKENDS, default="d3dmetal")
    s.add_argument("--sync", choices=graphics.SYNCS, default="msync")
    s.add_argument("--no-deps", action="store_true", help="ne pas installer vcrun2022, corefonts, d3dcompiler_47")
    s = add("list", _list, "lister les bouteilles")
    s.add_argument("--json", action="store_true")
    s = add("run", _run, "lancer un .exe, .msi ou .iso (ou un chemin C:\\…)")
    s.add_argument("name")
    s.add_argument("target")
    s.add_argument("args", nargs=argparse.REMAINDER)
    s = add("config", _config, "afficher ou changer les graphismes et la synchronisation")
    s.add_argument("name")
    s.add_argument("--graphics", choices=graphics.BACKENDS)
    s.add_argument("--sync", choices=graphics.SYNCS)
    s.add_argument("--json", action="store_true")
    s = add("delete", _delete, "supprimer une bouteille")
    s.add_argument("name")
    s.add_argument("--yes", action="store_true", help="confirmer la suppression")
    s = add("shortcut", _shortcut, "créer une app .app qui lance un programme en un clic")
    s.add_argument("name")
    s.add_argument("target", help='ex. "C:\\Games\\Jeu\\jeu.exe"')
    s.add_argument("--name", dest="label", help="nom de l'app")
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    clog.setup(a.verbose)
    try:
        code: int = a.fn(a)
        return code
    except CellierError as e:
        print(f"erreur : {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
