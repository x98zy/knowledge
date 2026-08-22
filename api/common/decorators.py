import asyncio
from functools import wraps


def retry_until_success(interval: list, slient: bool = False):
    def deco(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            for i in range(len(interval)):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if i < len(interval) - 1:
                        await asyncio.sleep(interval[i])
                        continue
                    else:
                        if not slient:
                            raise e

        return wrapped

    return deco
