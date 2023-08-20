import logging
import secrets
from pathlib import Path

from rich.logging import RichHandler

from vulnbooru.pages import app as app
from vulnbooru.pages import ui

logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)


STORAGE_SECRET_PATH = Path(".") / "storage_secret.txt"


def main():
    from nicegui import run

    run.APP_IMPORT_STRING = "vulnbooru:app"

    if STORAGE_SECRET_PATH.is_file():
        secret = STORAGE_SECRET_PATH.read_text().strip()
    else:
        STORAGE_SECRET_PATH.write_text(secret := secrets.token_urlsafe(16))
    ui.run(storage_secret=secret, show=False)


if __name__ == "__main__":
    main()
