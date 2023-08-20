import hashlib
import re
from logging import getLogger
from mimetypes import guess_extension
from os import environ
from pathlib import Path
from secrets import compare_digest
from tempfile import mktemp
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from nicegui import app, events, ui
from PIL import Image

from .loader import ModelLoader

logger = getLogger(__name__)

PASSWORD_SALT = "subscribe_taffy_thanks_meow!"
SALTED_PASSWORD = environ.get("SALTED_PASSWORD", "")

STATIC_PATH = Path("./static")

if not SALTED_PASSWORD:
    logger.warning("SALTED_PASSWORD not set, you will not be able to access admin page")


@app.get("/static/{file_path:path}")
def static(file_path: str):
    static_file = STATIC_PATH / file_path
    if not static_file.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(f"./static/{file_path}")


@ui.page("/")
def index_page():
    available_models = [*ModelLoader.available_models().keys()]

    image_file_path: Optional[str] = None

    def handle_upload(e: events.UploadEventArguments):
        if not e.type.startswith("image/") or (ext := guess_extension(e.type)) is None:
            ui.notify("Please upload an image with valid MIME type", color="negative")
            return

        with open(file_path := mktemp(suffix=ext), "wb") as f:
            total = 0
            for chunk in e.content:
                total += f.write(chunk)

        logger.debug(f"Uploaded file to {file_path} ({total} bytes)")
        nonlocal image_file_path
        image_file_path = file_path

    def predict(e: events.ClickEventArguments):
        if image_file_path is None:
            ui.notify("Please upload an image first", color="negative")
            return

        logger.debug(f"Predicting image {image_file_path} ...")
        upload_button.disable()
        spinner.set_visibility(True)

        image = Image.open(image_file_path)

        if ModelLoader.current_active_model is None:
            ui.notify("Please select a model first", color="negative")
            return

        result = ModelLoader.predict(image, prob_threshold.value)
        tag_chart.options["series"] = [
            {"name": tag, "data": [prob * 100]} for tag, prob in result.items()
        ]
        tag_chart.update()

        upload_button.enable()
        spinner.set_visibility(False)

    def update_model(e: events.ValueChangeEventArguments):
        logger.info(f"Loading model {e.value!r} ...")
        model_selector.disable()
        spinner.set_visibility(True)
        try:
            ModelLoader(e.value).load()
        except Exception as err:
            ui.notify(f"Failed to load model {e.value!r}: {err}", color="negative")
            logger.exception(err)
        spinner.set_visibility(False)
        model_selector.enable()

    with ui.carousel(animated=True, navigation=True).props("autoplay").classes(
        "z-0 fullscreen"
    ):
        for image in STATIC_PATH.glob("background*"):
            with ui.carousel_slide().classes("p-0"):
                ui.image(f"/static/{image.name}").classes("h-full").props("fit=cover")

    with ui.row().classes(
        "justify-center items-center w-full absolute-center z-10"
    ), ui.card().classes("col-12 col-md-10 col-xl-8 bg-white/70 backdrop-blur-sm"):
        with ui.card_section(), ui.row():
            ui.label("Welcome to VulnBooru!").classes("text-h4")
            spinner = ui.spinner(size="lg")
            spinner.set_visibility(False)

        with ui.card_section(), ui.row():
            with ui.column().classes("col-6 items-stretch justify-center"):
                model_selector = ui.select(
                    available_models,
                    label="Available checkpoints",
                    value=ModelLoader.current_active_model.name
                    if ModelLoader.current_active_model
                    else None,
                    on_change=update_model,
                )
                ui.upload(
                    label="Upload image", on_upload=handle_upload, auto_upload=True
                )
                with ui.row():
                    ui.label("Probability threshold")
                    prob_threshold = ui.slider(min=0, max=1, value=0.5, step=0.001)
                upload_button = ui.button(
                    "Predict Now", icon="play_circle_filled", on_click=predict
                ).props("outline rounded")

            with ui.card_section().classes("col-6"):
                tag_chart = ui.chart(
                    {
                        "title": "Tag Probabilities",
                        "chart": {
                            "type": "packedbubble",
                            "backgroundColor": None,
                        },
                        "tooltip": {
                            "useHTML": True,
                            "pointFormat": "{point.value:.3f}%",
                        },
                        "plotOptions": {
                            "packedbubble": {
                                "minSize": "20%",
                                "maxSize": "100%",
                                "zMin": 0,
                                "zMax": 100,
                                "layoutAlgorithm": {
                                    "splitSeries": False,
                                    "gravitationalConstant": 0.02,
                                },
                            },
                        },
                        "series": [],
                    }
                )


def authorization_middleware(
    credentials: Optional[HTTPBasicCredentials] = Depends(
        HTTPBasic(auto_error=False),
    ),
):
    if credentials is not None and (
        compare_digest(credentials.username, "admin")
        and compare_digest(
            hashlib.sha256(
                f"{PASSWORD_SALT}{credentials.password}{PASSWORD_SALT}".encode()
            ).hexdigest(),
            SALTED_PASSWORD,
        )
    ):
        app.storage.browser["is_admin"] = True
    is_admin = app.storage.browser.get("is_admin", False)
    if not is_admin:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return is_admin


@ui.page("/admin")
def admin_page(is_admin: bool = Depends(authorization_middleware)):
    def handle_upload(e: events.UploadEventArguments):
        name = str.strip(model_name_input.value)
        if not name:
            ui.notify("Please input a valid model name", color="negative")
            return
        with open(ModelLoader.model_path / f"{name}.pt", "wb") as f:
            total = 0
            for chunk in e.content:
                total += f.write(chunk)
        logger.debug(f"New model {name=} uploaded, {total} bytes")
        ui.open(admin_page)

    with ui.dialog() as upload_dialog, ui.card():
        with ui.card_section():
            ui.label("Upload Model").classes("text-h6")

        with ui.card_section(), ui.column().classes("items-stretch"):
            model_name_input = ui.input(
                "Model Name",
                validation={
                    "Please input a valid filename.": lambda value: re.fullmatch(
                        r"^[a-zA-Z0-9_\-]+$", value
                    )
                    is not None
                },
            )
            ui.upload(label="Model File", auto_upload=True, on_upload=handle_upload)
            ui.button("Cancel", on_click=upload_dialog.close).props("flat")

    with ui.row().classes(
        "w-full absolute-center justify-center items-center"
    ), ui.card().classes("col-12 col-md-10 col-xl-8"):
        with ui.card_section(), ui.row():
            ui.label("Welcome, Admin!").classes("text-h5")

        with ui.card_section(), ui.column().classes("items-stretch"):
            for index, (model_name, _) in enumerate(
                ModelLoader.available_models().items()
            ):
                splitter = ui.splitter(horizontal=True)
                with splitter.before, ui.row().classes(
                    "items-center justify-between q-mb-md"
                ):
                    ui.label(f"{index+1}. Model:").classes("text-body1")
                    ui.label(model_name).classes("text-body2 font-mono")
                    ui.button(
                        "Delete",
                        icon="delete",
                        color="negative",
                        on_click=lambda e: (
                            ModelLoader.delete_model(model_name),
                            ui.open(admin_page),
                        ),
                    ).props("flat")

        with ui.card_actions():
            ui.button("Upload Model", icon="upload", on_click=upload_dialog.open)
            ui.button("Refresh", icon="refresh", on_click=lambda e: ui.open(admin_page))
