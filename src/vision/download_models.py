"""Download the local YOLOv4-tiny model files."""

from __future__ import annotations

from urllib.request import urlretrieve

from src import config


def download_models() -> None:
    """Save model configuration and weights to the configured models folder."""
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for url, destination in (
        (config.CAR_MODEL_CONFIG_URL, config.CAR_MODEL_CONFIG_PATH),
        (config.CAR_MODEL_WEIGHTS_URL, config.CAR_MODEL_WEIGHTS_PATH),
    ):
        if destination.exists():
            continue
        temporary = destination.with_suffix(destination.suffix + ".download")
        try:
            urlretrieve(url, temporary)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    download_models()
