import multiprocessing

from nicegui import globals

from vulnbooru.pages import app as app

if (
    not globals.ui_run_has_been_called
    and multiprocessing.current_process().name != "MainProcess"
):
    from .__main__ import main

    main()

__all__ = ["app"]
