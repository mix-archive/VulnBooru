import time
from logging import getLogger
from pathlib import Path
from typing import ClassVar, Dict, Optional

import numpy
import torch
from PIL.Image import Image

from .model import DeepDanbooruModel

logger = getLogger(__name__)

MODEL_PATH = Path("./checkpoints")


class ModelLoader:
    current_active_model: ClassVar[Optional["ModelLoader"]] = None
    ready = False

    @staticmethod
    def available_models() -> Dict[str, Path]:
        return {path.stem: path for path in MODEL_PATH.glob("*.pt")}

    def __init__(self, name: str) -> None:
        self.name = name
        self.model = DeepDanbooruModel()
        self.checkpoint_path = self.available_models()[name]

    def load(self) -> None:
        logger.debug(f"Loading model from {self.checkpoint_path} ...")
        weights = torch.load(self.checkpoint_path)
        self.model.load_state_dict(weights)
        self.model.eval()
        self.__class__.current_active_model = self

        logger.debug("Model loaded, test predicting ...")
        test_tensor = torch.rand(1, 512, 512, 3)
        self._predict(test_tensor)
        logger.debug("Model test passed")

        self.ready = True

    def _predict(self, x: torch.Tensor) -> torch.Tensor:
        assert x.shape == (1, 512, 512, 3), "Input shape must be (1, 512, 512, 3)"

        logger.debug("Predicting input image ...")
        start_time = time.time()
        try:
            predicted = self.model(x)
        except Exception as e:
            logger.exception(e)
            raise e
        time_delta = (time.time() - start_time) * 1000
        logger.debug(f"Predicted result in {time_delta:.2f}ms")
        return predicted

    @classmethod
    def predict(cls, image: Image, prob_threshold: float = 0.5) -> Dict[str, float]:
        assert (loaded := cls.current_active_model) is not None, "Model not loaded yet"
        assert loaded.ready, "Model not ready yet"

        image = image.convert("RGB").resize((512, 512))
        tensor = torch.from_numpy(
            numpy.expand_dims(
                numpy.array(image, dtype=numpy.float32),
                0,
            )
            / 255
        )

        with torch.no_grad():
            result, *_ = loaded._predict(tensor)
            tag_prob = result.detach().numpy()
        return {
            tag: prob
            for tag, prob in zip(loaded.model.tags, tag_prob)
            if prob >= prob_threshold
        }
