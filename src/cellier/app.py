"""Point d'entrée de Cellier.app : sans argument → interface graphique, sinon → CLI."""

import sys

from cellier import cli


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("-psn_")]  # argument ajouté par le Finder
    if args:
        sys.exit(cli.main(args))
    from cellier import gui  # tkinter chargé seulement pour l'interface

    gui.run()
