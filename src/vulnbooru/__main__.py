import logging
import secrets
from os import environ
from pathlib import Path

import dotenv
from rich.logging import RichHandler

from vulnbooru.pages import app as app
from vulnbooru.pages import ui

logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger(__name__)

dotenv.load_dotenv()

SECRET_PATH = Path("/tmp/vulnbooru_secret")


def main():
    from nicegui import run

    run.APP_IMPORT_STRING = "vulnbooru:app"

    if not SECRET_PATH.is_file():
        SECRET_PATH.write_text(secret := secrets.token_urlsafe(16))
        logger.info("New secret storage file created.")
    else:
        secret = SECRET_PATH.read_text().strip()

    ui.run(
        host=environ.get("HOST"),
        port=int(environ.get("PORT", 8080)),
        title="VulnBooru",
        storage_secret=secret,
        show=False,
    )


if __name__ == "__main__":
    main()
