import os
from pathlib import Path


def to_path(*args: str) -> Path:
    return Path(os.path.join(*args)).resolve()
