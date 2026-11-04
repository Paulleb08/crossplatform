# Cellier : règles du projet

Gestionnaire open source de bouteilles Wine pour macOS Apple Silicon, alternative légère à CrossOver.
Uniquement des briques libres (Wine, DXVK, MoltenVK, Winetricks) et les outils gratuits d'Apple (Game Porting Toolkit / D3DMetal, Rosetta 2, `hdiutil`).

## Stack technique

| Brique | Rôle | Source |
|---|---|---|
| Wine (`wine64`, `wineboot`, `winecfg`) | Couche Win32 → macOS, tourne sous Rosetta 2 | Homebrew (tap `gcenx/wine`) ou build GPTK |
| D3DMetal (GPTK) | Traduction DirectX 11/12 → Metal | Apple Developer (gratuit, compte requis) |
| DXVK (fork macOS) + MoltenVK | DirectX 9-11 → Vulkan → Metal | `brew install molten-vk`, DXVK-macOS |
| MSync / ESync | Synchronisation rapide des threads (`WINEMSYNC=1` / `WINEESYNC=1`) | intégré aux builds Wine GPTK |
| Winetricks | Runtimes : `vcrun2022` (couvre 2015-2022), `corefonts`, `d3dcompiler_47` | `brew install winetricks` |
| `hdiutil` | Montage des ISO (`attach -nobrowse -readonly`) | macOS |

## Architecture

```
src/cellier/
  core/            # moteur pur, testable sans Wine (aucun import de cli/)
    errors.py      # CellierError et sous-classes
    process.py     # exécution capturée des outils (wine64, winetricks, hdiutil)
    paths.py       # chemins ~/Library/Application Support/Cellier, ~/Library/Logs/Cellier
    log.py         # configuration logging (fichier + console)
    prefix.py      # Jalon 1 : création/liste/suppression des préfixes WINEPREFIX
    deps.py        # Jalon 1 : winetricks
    graphics.py    # Jalon 2 : bascule D3DMetal <-> DXVK, MSync/ESync
    runner.py      # Jalon 3 : lancement wine64, capture stdout/stderr, codes retour
    media.py       # Jalon 3 : détection .exe/.msi/.iso + montage hdiutil
    shortcuts.py   # Jalon 4 : scripts .command et bundles .app
  cli/             # Jalon 4 : argparse, sous-commandes create/list/run/config/delete
tests/             # unittest stdlib, un fichier par module core
docs/guide.html    # guide utilisateur illustré
```

Interface SwiftUI future : elle n'appellera que la CLI avec `--json`. Toute sortie
lisible par une machine passe donc par des dataclasses sérialisables, jamais par du texte formaté.

## Emplacements sur le Mac

- Bouteilles : `~/Library/Application Support/Cellier/Bottles/<nom>/` (contient `prefix/` + `bottle.json`)
- Logs : `~/Library/Logs/Cellier/<bouteille>/<date>.log`
- Raccourcis : `~/Applications/Cellier/<App>.app`
- Toute racine est surchargeable par `CELLIER_HOME` (indispensable pour les tests).

## Règles de code

- Python 3.11+, **bibliothèque standard uniquement** (pas de pip). Config en JSON (lecture et écriture en stdlib).
- Typage strict : chaque fonction est annotée, `mypy --strict` doit passer.
- `pathlib.Path` partout, jamais de chemins en chaînes concaténées.
- Sous-processus : `subprocess.run([...], check=False, capture_output=True, text=True, stdin=DEVNULL)`.
  Jamais `shell=True`. Le code retour est toujours vérifié.
- Erreurs : une hiérarchie `CellierError` (`core/errors.py`) avec des sous-classes précises
  (`WineNotFound`, `BottleExists`, `BottleNotFound`, `MountFailed`…). La CLI les attrape,
  affiche un message clair et sort avec un code ≠ 0. Pas de `except Exception` silencieux.
- Logs via `logging.getLogger(__name__)`, jamais `print` dans `core/`.
- Suppression d'une bouteille : vérifier que le chemin est bien sous la racine Cellier avant `rmtree`.
- Tests : Wine n'est jamais appelé pour de vrai. On injecte un faux binaire (script shell dans un dossier temporaire) ou on simule `subprocess.run`.

## Commandes

```bash
PYTHONPATH=src:tests python3 -m unittest discover -s tests   # tests (faux Wine, tourne aussi sous Linux)
python3 -m mypy                                              # typage strict (pip install mypy, outil de dev)
PYTHONPATH=src python3 -m cellier --help                     # CLI
```

Variables utiles : `CELLIER_HOME` (racine unique, tests), `CELLIER_WINE`, `CELLIER_WINETRICKS`, `CELLIER_DXVK` (dossier des DLL x64 DXVK).

## Leçons apprises (à relire avant de travailler, à compléter après chaque erreur)

Une ligne par leçon : l'erreur, puis la règle.

- Hook GateGuard (Bash/Write) : il bloque le premier appel tant que les faits ne sont pas donnés. Annoncer la demande et le but de la commande dès le premier message, puis enchaîner les fichiers via `cat <<'EOF'` dans un seul appel Bash.
- Un `/goal` qui décrit le produit complet ne s'arrête pas à un squelette et une demande de feu vert. Livrer les fonctionnalités et les tests dans la même session.
- Bascule DXVK appelée deux fois : la DLL DXVK était sauvegardée comme originale. Une sauvegarde ne se fait qu'au premier passage. Tester toute opération réversible par un aller-retour et un double appel.
- `mypy` sans `files` dans `pyproject.toml` sort en erreur. Garder `files = ["src"]`.
- Économie de tokens : regrouper les écritures de fichiers, lancer tests et mypy dans le même appel, ne pas relire un fichier qu'on vient d'écrire, éditer par un remplacement ciblé plutôt que tout réécrire.
- Noms de paquets Homebrew tiers (`gcenx/wine/...`) non vérifiables hors ligne : les signaler comme à confirmer, ne pas les présenter comme sûrs.
- `rm -rf` dans une commande déclenche le hook destructif. Les artefacts de build sont déjà dans `.gitignore` : ne pas les supprimer, ne jamais mêler suppression et commit.
