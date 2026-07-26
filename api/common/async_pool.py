import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


class AsyncTaskResult:
    """
    异步任务执行结果
    """

    def __init__(self, task_id: int, result: T | None = None, exception: Exception | None = None):
        self.task_id = task_id
        self.result = result
        self.exception = exception

    @property
    def success(self) -> bool:
        return self.exception is None

    def __repr__(self) -> str:
        if self.success:
            return f"AsyncTaskResult(task_id={self.task_id}, result={self.result})"
        return f"AsyncTaskResult(task_id={self.task_id}, exception={self.exception})"


class AsyncExecutorPool:
    """
    异步协程并发执行池，类似 ThreadPoolExecutor，但用于协程

    使用 Semaphore 控制最大并发数，提供任务提交、结果收集等功能
    """

    def __init__(self, max_concurrency: int = 5):
        """
        初始化异步执行池

        :param max_concurrency: 最大并发数，默认为5
        """
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._tasks: list[asyncio.Task] = []
        self._task_id_counter = 0

    @property
    def max_concurrency(self) -> int:
        """
        获取最大并发数
        """
        return self._max_concurrency

    @property
    def active_count(self) -> int:
        """
        获取当前活跃任务数
        """
        return self._max_concurrency - self._semaphore._value

    async def _wrap_task(
        self, func: Callable[..., Awaitable[T]], task_id: int, *args: Any, **kwargs: Any
    ) -> AsyncTaskResult:
        """
        包装任务执行，添加信号量控制和异常处理

        :param func: 异步函数
        :param task_id: 任务ID
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 任务执行结果
        """
        async with self._semaphore:
            try:
                result = await func(*args, **kwargs)
                return AsyncTaskResult(task_id=task_id, result=result)
            except Exception as e:
                return AsyncTaskResult(task_id=task_id, exception=e)

    def submit(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> asyncio.Task[AsyncTaskResult]:
        """
        提交一个异步任务到执行池

        :param func: 异步函数
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: asyncio.Task 对象
        """
        self._task_id_counter += 1
        task = asyncio.create_task(self._wrap_task(func, self._task_id_counter, *args, **kwargs))
        self._tasks.append(task)
        return task

    async def gather(self, return_exceptions: bool = False) -> list[AsyncTaskResult]:
        """
        等待所有已提交任务完成，并收集结果

        :param return_exceptions: 是否将异常作为结果返回而不是抛出
        :return: 任务结果列表
        """
        if not self._tasks:
            return []

        results = await asyncio.gather(*self._tasks, return_exceptions=return_exceptions)
        self._tasks.clear()
        return results

    async def map(self, func: Callable[..., Awaitable[T]], *iterables: Any) -> list[AsyncTaskResult]:
        """
        并行执行多个任务，类似 asyncio.gather + Semaphore 控制

        :param func: 异步函数，接受与 iterables 对应的参数
        :param iterables: 可迭代参数序列
        :return: 任务结果列表，顺序与输入一致
        """
        tasks = []
        for args in zip(*iterables):
            tasks.append(self.submit(func, *args))

        results = await asyncio.gather(*tasks)
        self._tasks.clear()
        return results

    async def __aenter__(self) -> "AsyncExecutorPool":
        """
        支持 async with 上下文管理器
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        上下文退出时等待所有任务完成
        """
        await self.gather()


class AsyncBoundedSemaphore:
    """
    带边界的异步信号量，提供更简洁的并发控制方式

    使用示例：
    ```python
    semaphore = AsyncBoundedSemaphore(max_concurrent=5)

    @semaphore.limit
    async def fetch(url):
        return await http_client.get(url)
    ```
    """

    def __init__(self, max_concurrent: int = 5):
        """
        初始化信号量

        :param max_concurrent: 最大并发数
        """
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def limit(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """
        装饰器：限制函数的并发调用数

        :param func: 异步函数
        :return: 包装后的函数
        """

        async def wrapper(*args: Any, **kwargs: Any) -> T:
            async with self._semaphore:
                return await func(*args, **kwargs)

        return wrapper

    async def run(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """
        在信号量控制下执行异步函数

        :param func: 异步函数
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 函数执行结果
        """
        async with self._semaphore:
            return await func(*args, **kwargs)
