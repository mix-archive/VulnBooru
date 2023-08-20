import logging
import multiprocessing

from nicegui import globals
from rich.logging import RichHandler

from vulnbooru.pages import app as app

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[RichHandler(rich_tracebacks=True)],
)


if (
    not globals.ui_run_has_been_called
    and multiprocessing.current_process().name != "MainProcess"
):
    from .__main__ import main

    main()


__all__ = ["app"]
