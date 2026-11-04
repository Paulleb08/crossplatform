# Cellier

Lancez vos logiciels et jeux Windows 64-bit sur un Mac Apple Silicon, avec uniquement des outils gratuits et open source.

- **Installer** : téléchargez `Cellier.dmg` (artefact « Cellier-dmg » de la CI macOS, ou la release), glissez Cellier dans Applications, puis clic droit → Ouvrir au premier lancement.
- Guide pas à pas pour lancer un `.exe` : [`docs/guide.html`](docs/guide.html)
- Avancement : [`ROADMAP.md`](ROADMAP.md) · Règles de contribution : [`CLAUDE.md`](CLAUDE.md)

> État : app graphique et CLI. La CI tourne sur macOS Apple Silicon : tests, montage ISO réel, ouverture de l'interface, DMG, et un essai Wine/GPTK réel (création d'une bouteille avec winetricks, puis `cmd.exe` → « Microsoft Windows 10.0.19043 »).

```bash
git clone https://github.com/paulleb08/crossplatform && cd crossplatform
pip3 install --user .            # installe la commande `cellier` (aucune dépendance)
cellier create MesJeux           # Windows 10 64-bit + vcrun2022, corefonts, d3dcompiler_47
cellier run MesJeux ~/Downloads/setup.exe     # .exe, .msi ou .iso
cellier shortcut MesJeux "C:\Games\Jeu\jeu.exe" --name "Mon Jeu"
cellier config MesJeux --graphics dxvk --sync esync
cellier list | cellier delete MesJeux --yes
```

Tests : `PYTHONPATH=src:tests python3 -m unittest discover -s tests`

Licence MIT.
