from fastapi import FastAPI

from config.settings import settings


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    from scripts.init_app import init_app

    app = FastAPI(**settings.FASTAPI_CONFIG)
    init_app(app)
    return app


app = create_app()
