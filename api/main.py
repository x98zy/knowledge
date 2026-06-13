from api.config.settings import settings
from fastapi import FastAPI


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    from api.scripts.init_app import init_app

    app = FastAPI(**settings.FASTAPI_CONFIG)
    init_app(app)
    return app


app = create_app()
