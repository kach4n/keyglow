"""KeyGlow desktop app entry point.

--smoke-test opens the window, waits for the UI to load, then exits with
status 0 (used by CI to check that a built app really starts).
"""

import sys
import threading
from pathlib import Path

import webview

from keyglow import __version__
from keyglow.api import Api


def _web_dir():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / "keyglow" / "web"


def _timer(seconds, fn):
    t = threading.Timer(seconds, fn)
    t.daemon = True
    t.start()


def main():
    smoke = "--smoke-test" in sys.argv
    api = Api()
    window = webview.create_window(f"KeyGlow {__version__}", str(_web_dir() / "index.html"), js_api=api,
                                   width=1280, height=820, min_size=(980, 680), background_color="#0d0f14")
    loaded = threading.Event()

    def on_loaded():
        title = window.evaluate_js("document.title")
        print(f"UI loaded: {title}", flush=True)
        loaded.set()
        if smoke:
            _timer(2, window.destroy)

    window.events.loaded += on_loaded
    if smoke:
        _timer(60, window.destroy)      # give up if the UI never loads
    try:
        webview.start(gui="qt" if sys.platform.startswith("linux") else None)
    finally:
        api.shutdown()
    if smoke and not loaded.is_set():
        sys.exit("Smoke test failed: UI did not load")


if __name__ == "__main__":
    main()
