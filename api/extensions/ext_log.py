import sys

from loguru import logger


def setup_logger() -> None:
    """配置全局日志"""
    logger.remove()  # 移除默认配置

    # 控制台日志
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
    )

    # 文件日志: 按日期分割, 保留 30 天, 按 100MB 轮转
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="100 MB",
        retention="30 days",
        encoding="utf-8",
        enqueue=True,  # 多进程安全
    )


setup_logger()

__all__ = ["logger"]
