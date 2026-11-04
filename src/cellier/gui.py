"""Interface graphique (tkinter, stdlib). Les opérations longues tournent dans des threads."""

import logging
import queue
import subprocess
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from cellier import __version__
from cellier.core import deps, graphics, log as clog, paths, prefix, prereqs, runner, shortcuts
from cellier.core.errors import CellierError

log = logging.getLogger("cellier.gui")
STEPS = "① Prérequis   →   ② Nouvelle bouteille   →   ③ Lancer un programme   →   ④ Créer un raccourci"
GRAPHICS = {"d3dmetal": "D3DMetal : DirectX 11/12, recommandé", "dxvk": "DXVK : DirectX 9 à 11, jeux anciens"}
SYNCS = {"msync": "MSync : le plus rapide", "esync": "ESync : si un jeu se fige", "off": "Désactivée"}


class _ToGui(logging.Handler):
    def __init__(self, app: "App") -> None:
        super().__init__(logging.INFO)
        self.app = app

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.app.post(lambda: self.app.append_log(msg))


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.events: queue.Queue[Callable[[], None]] = queue.Queue()
        self.busy = False
        self.bottles: list[prefix.Bottle] = []
        root.title("Cellier")
        root.geometry("900x640")
        root.minsize(780, 560)
        self.gfx = tk.StringVar(value="d3dmetal")
        self.sync = tk.StringVar(value="msync")
        self.title = tk.StringVar()
        self.prereq = tk.StringVar()
        self.status = tk.StringVar(value="Prêt.")
        self._build()
        logging.getLogger("cellier").addHandler(_ToGui(self))
        self.refresh()
        self.check_prereqs()
        root.after(100, self._drain)

    # --- construction -------------------------------------------------
    def _build(self) -> None:
        pad: dict[str, Any] = {"padx": 12, "pady": 6}
        top = ttk.Frame(self.root)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Cellier", font=("Helvetica", 22, "bold")).pack(side="left")
        ttk.Label(top, text=f"  v{__version__} · programmes Windows sur Mac").pack(side="left")
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=12)
        self.prereq_label = ttk.Label(bar, textvariable=self.prereq)
        self.prereq_label.pack(side="left")
        ttk.Button(bar, text="Vérifier à nouveau", command=self.check_prereqs).pack(side="right")
        self.install_btn = ttk.Button(bar, text="Installer les prérequis…", command=self.install_prereqs)
        self.install_btn.pack(side="right", padx=6)
        ttk.Label(self.root, text=STEPS, foreground="#7a1f3d").pack(fill="x", **pad)

        body = ttk.PanedWindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=12)
        left = ttk.Frame(body, padding=6)
        body.add(left, weight=1)
        ttk.Label(left, text="Bouteilles", font=("Helvetica", 14, "bold")).pack(anchor="w")
        self.listbox = tk.Listbox(left, height=10, exportselection=False, activestyle="none")
        self.listbox.pack(fill="both", expand=True, pady=6)
        self.listbox.bind("<<ListboxSelect>>", lambda _e: self.show_selected())
        row = ttk.Frame(left)
        row.pack(fill="x")
        ttk.Button(row, text="Nouvelle…", command=self.new_bottle).pack(side="left")
        self.delete_btn = ttk.Button(row, text="Supprimer…", command=self.delete_bottle)
        self.delete_btn.pack(side="right")

        right = ttk.Frame(body, padding=6)
        body.add(right, weight=3)
        ttk.Label(right, textvariable=self.title, font=("Helvetica", 14, "bold"), wraplength=520).pack(anchor="w")
        self.controls: list[ttk.Radiobutton | ttk.Button] = []
        box = ttk.LabelFrame(right, text="Moteur graphique", padding=8)
        box.pack(fill="x", pady=6)
        for key, label in GRAPHICS.items():
            w = ttk.Radiobutton(box, text=label, value=key, variable=self.gfx, command=self.apply_settings)
            w.pack(anchor="w")
            self.controls.append(w)
        box = ttk.LabelFrame(right, text="Synchronisation", padding=8)
        box.pack(fill="x", pady=6)
        for key, label in SYNCS.items():
            w = ttk.Radiobutton(box, text=label, value=key, variable=self.sync, command=self.apply_settings)
            w.pack(anchor="w")
            self.controls.append(w)
        acts = ttk.LabelFrame(right, text="Actions", padding=8)
        acts.pack(fill="x", pady=6)
        for text, cmd in (("▶  Lancer un programme… (.exe, .msi, .iso)", self.launch),
                          ("Créer un raccourci dans le Dock…", self.make_shortcut),
                          ("Ouvrir le disque C:", self.open_drive_c),
                          ("Ouvrir les journaux", self.open_logs)):
            b = ttk.Button(acts, text=text, command=cmd)
            b.pack(fill="x", pady=2)
            self.controls.append(b)

        bottom = ttk.Frame(self.root)
        bottom.pack(fill="both", padx=12, pady=(6, 0))
        self.logbox = tk.Text(bottom, height=8, state="disabled", wrap="word", font=("Menlo", 11))
        scroll = ttk.Scrollbar(bottom, command=self.logbox.yview)
        self.logbox.configure(yscrollcommand=scroll.set)
        self.logbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        foot = ttk.Frame(self.root)
        foot.pack(fill="x", padx=12, pady=6)
        ttk.Label(foot, textvariable=self.status).pack(side="left")
        self.progress = ttk.Progressbar(foot, mode="indeterminate", length=160)
        self.progress.pack(side="right")

    # --- boucle d'événements ------------------------------------------
    def post(self, fn: Callable[[], None]) -> None:
        self.events.put(fn)

    def _drain(self) -> None:
        while not self.events.empty():
            self.events.get_nowait()()
        self.root.after(100, self._drain)

    def append_log(self, msg: str) -> None:
        self.logbox.configure(state="normal")
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def task(self, label: str, fn: Callable[[], object], done: Callable[[object], None] | None = None,
             exclusive: bool = True) -> None:
        """Exécute fn dans un thread ; exclusive=False pour un jeu qui tourne longtemps."""
        if exclusive and self.busy:
            messagebox.showinfo("Patientez", "Une opération est déjà en cours.", parent=self.root)
            return
        if exclusive:
            self.busy = True
            self.progress.start(12)
        self.status.set(label)

        def finish(ok: bool) -> None:
            if exclusive:
                self.busy = False
                self.progress.stop()
            self.status.set("Prêt." if ok else "Échec, voir le journal ci-dessus.")
            self.refresh()

        def work() -> None:
            try:
                result = fn()
            except CellierError as e:
                msg = str(e)
                log.error("%s", msg)
                def fail() -> None:
                    finish(False)
                    messagebox.showerror("Cellier", msg, parent=self.root)
                self.post(fail)
                return
            except Exception:  # noqa: BLE001 - un bug ne doit pas figer l'interface
                log.exception("erreur inattendue")
                self.post(lambda: finish(False))
                return

            def ok() -> None:
                finish(True)
                if done:
                    done(result)
            self.post(ok)

        threading.Thread(target=work, daemon=True).start()

    # --- état ---------------------------------------------------------
    def selected(self) -> prefix.Bottle | None:
        sel: tuple[int, ...] = self.listbox.curselection()  # type: ignore[no-untyped-call]
        return self.bottles[sel[0]] if sel and sel[0] < len(self.bottles) else None

    def refresh(self, select: str | None = None) -> None:
        current = select or (b.name if (b := self.selected()) else None)
        self.bottles = prefix.list_bottles()
        self.listbox.delete(0, "end")
        for i, b in enumerate(self.bottles):
            self.listbox.insert("end", f"  {b.name}")
            if b.name == current or (current is None and i == 0):
                self.listbox.selection_set(i)
        self.show_selected()

    def show_selected(self) -> None:
        b = self.selected()
        state = "normal" if b and not self.busy else "disabled"
        for w in self.controls:
            w.configure(state=state)
        self.delete_btn.configure(state="normal" if b else "disabled")
        if b is None:
            self.title.set("Aucune bouteille. Cliquez sur « Nouvelle… » pour créer votre premier Windows.")
            return
        self.title.set(f"{b.name}  ·  Windows 10 64-bit")
        self.gfx.set(b.graphics)
        self.sync.set(b.sync)

    def check_prereqs(self) -> None:
        found = prereqs.status()
        missing = [n for n, p in found.items() if p is None]
        if missing:
            self.prereq.set(f"✗ Manquant : {', '.join(missing)}. Cliquez sur « Installer les prérequis… ».")
            self.prereq_label.configure(foreground="#b3261e")
            self.install_btn.pack(side="right", padx=6)
        else:
            self.prereq.set(f"✓ Wine prêt : {found['wine']}")
            self.prereq_label.configure(foreground="#1f7a4d")
            self.install_btn.pack_forget()

    # --- actions ------------------------------------------------------
    def install_prereqs(self) -> None:
        if not messagebox.askokcancel(
                "Installer les prérequis",
                "Un Terminal va s'ouvrir et installer Rosetta 2, Homebrew, Wine (Game Porting Toolkit) "
                "et Winetricks. Votre mot de passe Mac peut être demandé. Comptez 10 à 20 minutes.",
                parent=self.root):
            return
        subprocess.run(["open", "-a", "Terminal", str(prereqs.write_script())], check=False)

    def new_bottle(self) -> None:
        name = simpledialog.askstring("Nouvelle bouteille", "Nom de la bouteille (ex. MesJeux) :", parent=self.root)
        if not name:
            return
        name = name.strip()
        with_deps = messagebox.askyesno(
            "Composants Windows",
            "Installer aussi Visual C++ 2015-2022, les polices Windows et d3dcompiler_47 ?\n"
            "Recommandé : la plupart des jeux en ont besoin. Comptez quelques minutes.", parent=self.root)

        def work() -> object:
            b = prefix.create(name)
            graphics.configure(b, "d3dmetal", "msync")
            if with_deps:
                deps.install(b)
            return b

        def created(_b: object) -> None:
            self.refresh(select=name)
            log.info("Bouteille prête. Étape suivante : ▶ Lancer un programme.")

        self.task(f"Création de « {name} »…", work, created)

    def delete_bottle(self) -> None:
        b = self.selected()
        if b and messagebox.askyesno("Supprimer", f"Supprimer définitivement « {b.name} » et tous les programmes "
                                     "installés dedans ?", icon="warning", parent=self.root):
            self.task(f"Suppression de « {b.name} »…", lambda: prefix.delete(b.name))

    def apply_settings(self) -> None:
        b = self.selected()
        if b and (self.gfx.get(), self.sync.get()) != (b.graphics, b.sync):
            gfx, sync = self.gfx.get(), self.sync.get()
            self.task("Application des réglages…", lambda: graphics.configure(b, gfx, sync))

    def launch(self) -> None:
        b = self.selected()
        if not b:
            return
        path = filedialog.askopenfilename(
            parent=self.root, title="Programme Windows à lancer",
            filetypes=[("Programmes Windows", "*.exe *.msi *.iso"), ("Tous les fichiers", "*")])
        if path:
            self.task(f"{Path(path).name} tourne dans « {b.name} »…", lambda: runner.launch(b, path),
                      lambda code: log.info("Programme terminé (code %s).", code), exclusive=False)

    def make_shortcut(self) -> None:
        b = self.selected()
        if not b:
            return
        path = filedialog.askopenfilename(
            parent=self.root, title="Programme installé (dans le disque C:)",
            initialdir=str(b.prefix / "drive_c"), filetypes=[("Programmes", "*.exe")])
        if not path:
            return
        try:
            target = shortcuts.to_windows_path(b, Path(path))
        except ValueError:
            messagebox.showerror("Raccourci", "Choisissez un programme installé dans le disque C: de la bouteille.",
                                 parent=self.root)
            return
        name = simpledialog.askstring("Raccourci", "Nom de l'application :", initialvalue=Path(path).stem,
                                      parent=self.root)
        if not name:
            return
        try:
            app = shortcuts.create_app(b, target, name.strip())
        except CellierError as e:
            messagebox.showerror("Raccourci", str(e), parent=self.root)
            return
        subprocess.run(["open", "-R", str(app)], check=False)
        messagebox.showinfo("Raccourci créé", f"{app.name} est prêt dans {app.parent}.\n"
                            "Glissez-le dans le Dock pour lancer le programme en un clic.", parent=self.root)

    def open_drive_c(self) -> None:
        if b := self.selected():
            subprocess.run(["open", str(b.prefix / "drive_c")], check=False)

    def open_logs(self) -> None:
        d = paths.logs_dir() / (b.name if (b := self.selected()) else "")
        d.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(d)], check=False)


def run() -> None:
    clog.setup(False)
    root = tk.Tk()
    App(root)
    root.mainloop()
