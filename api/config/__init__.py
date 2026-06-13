from pathlib import Path
from typing import Any

from pydantic import BaseModel

CONFIG_DIR = Path(__file__).parent


class Server(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    workers: int = 1


class Mysql(BaseModel):
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = ""
    charset: str = "utf8mb4"


class Redis(BaseModel):
    host: str = "127.0.0.1"
    port: int = 6379
    db: int = 0
    password: str = ""


class Logging(BaseModel):
    level: str = "INFO"
    file: str = "logs/app.log"


# Mapping: INI section name -> BaseModel class
_SECTION_MODEL_MAP: dict[str, type[BaseModel]] = {
    "Server": Server,
    "Mysql": Mysql,
    "Redis": Redis,
    "Logging": Logging,
}


def _coerce_type(field_type: type, value: str) -> Any:
    if field_type is bool:
        return value.lower() in ("true", "1", "yes", "on")
    if field_type is int:
        return int(value)
    if field_type is float:
        return float(value)
    return value


def load_ini(path: str | Path | None = None, *, env: str | None = None) -> dict[str, BaseModel]:
    """Load an INI config file and return a dict of section_name -> model instance.

    Args:
        path: Explicit path to the INI file. If omitted, ``env`` is used to
              resolve ``{CONFIG_DIR}/{env}.ini``.
        env: Environment name (``"dev"``, ``"prod"``, etc.). Ignored if
             ``path`` is provided.

    Raises:
        FileNotFoundError: when the resolved INI file does not exist.
        ValueError: when a section has no corresponding model class.
    """
    import configparser

    if path is None:
        if env is None:
            env = "dev"
        path = CONFIG_DIR / f"{env}.ini"

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")

    result: dict[str, BaseModel] = {}
    for section in parser.sections():
        model_cls = _SECTION_MODEL_MAP.get(section)
        if model_cls is None:
            raise ValueError(f"Unknown section [{section}] in {path}. Register it in _SECTION_MODEL_MAP.")

        fields: dict[str, Any] = {}
        model_fields = model_cls.model_fields
        for key, raw_value in parser.items(section):
            field_info = model_fields.get(key)
            if field_info is not None:
                fields[key] = _coerce_type(field_info.annotation, raw_value)
            else:
                fields[key] = raw_value

        result[section] = model_cls(**fields)

    return result


# Convenience: load dev or prod config
def load_dev() -> dict[str, BaseModel]:
    return load_ini(env="dev")


def load_prod() -> dict[str, BaseModel]:
    return load_ini(env="prod")
