# Cellier

Lancez vos logiciels et jeux Windows 64-bit sur un Mac Apple Silicon, avec uniquement des outils gratuits et open source.

- Guide pas à pas pour lancer un `.exe` : [`docs/guide.html`](docs/guide.html)
- Avancement : [`ROADMAP.md`](ROADMAP.md) · Règles de contribution : [`CLAUDE.md`](CLAUDE.md)

> État : les 4 jalons sont codés et testés avec un faux Wine. Ils n'ont pas encore été validés sur un vrai Mac.

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
