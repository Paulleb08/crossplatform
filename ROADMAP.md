# Feuille de route

Quatre jalons autonomes. Chacun se livre avec ses tests verts et ne dépend que des jalons précédents.
Le Jalon 1 inclut le socle commun (`errors.py`, `paths.py`, `log.py`).

## Jalon 1 : gestionnaire de préfixes WINEPREFIX

**Modules**
- `core/errors.py` : `CellierError` et ses sous-classes.
- `core/paths.py` : racines Application Support / Logs, surcharge `CELLIER_HOME`, détection de `wine64` et `winetricks` (PATH, puis emplacements Homebrew `/opt/homebrew/bin`, puis `CELLIER_WINE`).
- `core/log.py` : logger fichier + console.
- `core/prefix.py` : `create(name)`, `list()`, `get(name)`, `delete(name)`.
  Création : `WINEARCH=win64 WINEPREFIX=… wineboot --init`, puis version Windows 10 (`winecfg -v win10`), puis écriture de `bottle.toml`.
- `core/deps.py` : `install(bottle, verbs=("vcrun2022", "corefonts", "d3dcompiler_47"))` via `winetricks -q`.

**Tests exigés**
- création : bon environnement passé à `wineboot`, `bottle.toml` écrit, refus si le nom existe déjà ;
- noms invalides refusés (`../x`, vide, `/`) ;
- `list()` lit les bouteilles existantes et ignore les dossiers sans `bottle.toml` ;
- `delete()` refuse un chemin hors de la racine Cellier ;
- Wine ou Winetricks introuvable → `WineNotFound` avec un message qui dit comment l'installer ;
- échec de `winetricks` → erreur remontée avec la fin de son log.

## Jalon 2 : couche graphique D3DMetal / DXVK et MSync / ESync

**Modules**
- `core/graphics.py` :
  - `set_backend(bottle, "d3dmetal" | "dxvk")` : copie ou retire les DLL concernées (`d3d11`, `d3d12`, `dxgi`, `d3d10core`) dans `system32` et met à jour `WINEDLLOVERRIDES` ;
  - `set_sync(bottle, "msync" | "esync" | "off")` ;
  - `env_for(bottle) -> dict[str, str]` : variables d'environnement calculées depuis `bottle.toml` (`WINEMSYNC`, `WINEESYNC`, `WINEDLLOVERRIDES`, `DXVK_HUD`…).
- La bascule est à chaud : elle ne touche que `bottle.toml` et les DLL, sans recréer le préfixe.

**Tests exigés**
- `env_for` pour chaque combinaison backend × sync (table de cas) ;
- bascule D3DMetal → DXVK → D3DMetal : les DLL d'origine sont restaurées à l'identique ;
- refus clair si les fichiers GPTK ou DXVK sont absents ;
- MSync et ESync ne sont jamais actifs en même temps.

## Jalon 3 : runner de processus et médias

**Modules**
- `core/media.py` : `detect(path)` renvoie `exe`, `msi` ou `iso` (extension puis signature : `MZ` pour exe, OLE pour msi, `CD001` pour ISO).
  `mount(iso)` utilise `hdiutil attach -nobrowse -readonly -plist`, trouve le `setup.exe`/`autorun.inf` et démonte à la fin (`hdiutil detach`).
- `core/runner.py` : `run(bottle, target, args)` avec `.exe` → `wine64 target`, `.msi` → `wine64 msiexec /i target`.
  stdout et stderr sont écrits dans `~/Library/Logs/Cellier/<bouteille>/<horodatage>.log`. Le code retour est renvoyé, `wineserver -w` attend les processus enfants et Ctrl+C se termine proprement (`wineserver -k`).

**Tests exigés**
- `detect` sur de faux fichiers (bonne et mauvaise extension, signature) ;
- `mount` : sortie plist de `hdiutil` simulée → bon point de montage, démontage même en cas d'erreur ;
- `run` : commande et environnement exacts (faux `wine64`), log créé, code retour propagé ;
- un chemin Windows avec espaces reste un seul argument.

## Jalon 4 : CLI et raccourcis Mac

**Modules**
- `cli/__init__.py` : sous-commandes
  - `create NOM [--graphics d3dmetal|dxvk] [--sync msync|esync|off] [--no-deps]`
  - `list [--json]`
  - `run NOM FICHIER [-- args]` (accepte .exe, .msi, .iso)
  - `config NOM [--graphics …] [--sync …] [--show]`
  - `delete NOM [--yes]`
  - `shortcut NOM "C:\\…\\jeu.exe" [--name "Mon Jeu"]`
- `core/shortcuts.py` : script `.command` et bundle `.app` minimal (`Contents/MacOS/launch` + `Info.plist`) dans `~/Applications/Cellier/`.

**Tests exigés**
- chaque sous-commande : arguments analysés, bonne fonction core appelée, code de sortie ;
- une `CellierError` donne un message lisible et le code 1, sans trace Python ;
- `list --json` produit un JSON valide (contrat pour la future interface SwiftUI) ;
- le bundle `.app` généré a un `Info.plist` valide (`plistlib`) et un lanceur exécutable.

## Hors périmètre pour l'instant

Interface SwiftUI (préparée via `--json`), téléchargement automatique de GPTK (licence Apple), Windows 32-bit pur.
