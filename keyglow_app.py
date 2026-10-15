"""KeyGlow desktop app entry point."""

import sys
from pathlib import Path

import webview

from keyglow import __version__
from keyglow.api import Api


def _web_dir():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / "keyglow" / "web"


def main():
    api = Api()
    webview.create_window(f"KeyGlow {__version__}", str(_web_dir() / "index.html"), js_api=api,
                          width=1280, height=820, min_size=(980, 680), background_color="#0d0f14")
    try:
        webview.start()
    finally:
        api.shutdown()


if __name__ == "__main__":
    main()
