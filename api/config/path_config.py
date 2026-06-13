import os
from pathlib import Path

DIR = Path(__file__).parent.parent

ENV_DIR = os.path.join(DIR, "env")

LOG__DIR = os.path.join(DIR, "logs")
