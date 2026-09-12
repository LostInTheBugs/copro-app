"""Proprietas Desktop — lance le serveur local puis ouvre la fenêtre native.

Double-clic sur Proprietas.exe : le backend (uvicorn) démarre sur un port
local libre (127.0.0.1), la fenêtre s'ouvre sur l'application. Les données
vivent dans « data/ », à côté de l'exécutable — sauvegarder = copier ce
dossier, rien ne sort de la machine.

Variables d'environnement :
  PROPRIETAS_NO_WINDOW=1  → mode sans fenêtre (serveur seul ; tests, CI)
  PROPRIETAS_PORT=<port>  → port fixe (défaut : port libre automatique)
"""

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path


def base_dir() -> Path:
    """Dossier de travail : à côté de l'exécutable (bundle) ou racine du dépôt (dev)."""
    if getattr(sys, "frozen", False):  # exécutable PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Ressources embarquées (frontend_dist, alembic) : _MEIPASS ou dépôt (dev)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_server(port: int, tries: int = 300) -> bool:
    for _ in range(tries):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def screen_size() -> tuple:
    """Taille de l'écran (Windows) pour ne pas ouvrir plus grand que lui."""
    try:
        import ctypes

        u = ctypes.windll.user32
        return int(u.GetSystemMetrics(0)), int(u.GetSystemMetrics(1))
    except Exception:
        return 1280, 800


def prepare_env(base: Path, res: Path) -> None:
    """Configuration du serveur embarqué : SQLite + uploads dans data/."""
    data = base / "data"
    data.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(
        "COPRO_DATABASE_URL", "sqlite:///" + (data / "proprietas.db").as_posix()
    )
    os.environ.setdefault("COPRO_UPLOAD_DIR", str(data / "uploads"))
    os.environ.setdefault("COPRO_FRONTEND_DIST", str(res / "frontend_dist"))
    # Clé secrète persistée dans data/ : les sessions survivent au redémarrage.
    if "COPRO_SECRET_KEY" not in os.environ:
        keyfile = data / "secret.key"
        if keyfile.is_file():
            key = keyfile.read_text(encoding="utf-8").strip()
        else:
            key = os.urandom(32).hex()
            keyfile.write_text(key + "\n", encoding="utf-8")
        os.environ["COPRO_SECRET_KEY"] = key


def run_migrations(res: Path) -> None:
    """`alembic upgrade head` embarqué — crée/met à jour le schéma SQLite."""
    from alembic import command
    from alembic.config import Config as AlembicConfig

    cfg = AlembicConfig(str(res / "alembic.ini"))
    cfg.set_main_option("script_location", str(res / "alembic"))
    command.upgrade(cfg, "head")


class DesktopApi:
    """API JS → Python exposée à la page (window.pywebview.api.*).

    La WebView Windows n'exécute pas les téléchargements des liens vers
    l'API (exports PDF/CSV du serveur local) : le front intercepte ces clics
    et passe par « Enregistrer sous » natif (voir frontend/src/desktop.ts).
    """

    def save_file(self, filename: str, content: str, binary: bool = False, path=None) -> dict:
        import base64

        if not path:
            import webview

            win = webview.windows[0] if webview.windows else None
            if win is None:
                return {"ok": False, "error": "no-window"}
            chosen = win.create_file_dialog(webview.SAVE_DIALOG, save_filename=filename)
            if not chosen:
                return {"ok": False, "cancelled": True}
            path = chosen[0] if isinstance(chosen, (list, tuple)) else chosen
        target = Path(str(path))
        if binary:
            target.write_bytes(base64.b64decode(content))
        else:
            target.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(path)}


def main() -> None:
    # Binaire fenêtré (console=False) : stdout/stderr valent None sous Windows,
    # ce qui fait planter la configuration des logs d'uvicorn (isatty sur None).
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    base = base_dir()
    res = resource_dir()
    if not getattr(sys, "frozen", False):
        sys.path.insert(0, str(base / "backend"))  # dev : rendre « app » importable

    prepare_env(base, res)
    run_migrations(res)

    import uvicorn

    from app.main import app

    port = int(os.environ.get("PROPRIETAS_PORT") or 0) or free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    wait_server(port)

    if os.environ.get("PROPRIETAS_NO_WINDOW") == "1":
        # mode headless (tests/CI) : stdout peut être absent (binaire windowed)
        try:
            print(url, flush=True)
        except Exception:
            pass
        try:
            (base / "url.txt").write_text(url + "\n", encoding="utf-8")
        except Exception:
            pass
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
        return

    try:
        import webview  # fenêtre native (WebView2 sous Windows)

        sw, sh = screen_size()
        w = min(1280, max(960, sw - 80))
        h = min(880, max(640, sh - 120))
        webview.create_window(
            "Proprietas",
            url,
            width=w,
            height=h,
            min_size=(900, 600),
            js_api=DesktopApi(),
        )
        webview.start()  # bloque jusqu'à la fermeture de la fenêtre
        return
    except Exception:  # fenêtre indisponible → navigateur par défaut
        import webbrowser

        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:  # binaire fenêtré : consigner le crash dans error.log
        import traceback

        try:
            (base_dir() / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        raise
