"""
Concurrent user registration test script.

Usage:
    uv run python -m api.scripts.test_concurrent_register --concurrency 20 --total 100

Args:
    --concurrency:  max concurrent requests (default: 20)
    --total:        total number of requests (default: 100)
    --url:          registration endpoint URL (default: http://localhost:8000/api/v1/user/register)
"""

import argparse
import asyncio
import random
import string
import time

import httpx

BASE_URL = "http://localhost:8000/api/v1/user/register"


def random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def build_payload() -> dict:
    """生成合法的注册请求体"""
    suffix = random_string(6)
    return {
        "username": f"user_{suffix}",
        "email": f"{suffix}@test.com",
        "password": f"Test{suffix}!9",
        "confirm_password": f"Test{suffix}!9",
    }


async def register_one(client: httpx.AsyncClient, url: str, index: int) -> dict:
    """发起单次注册请求"""
    payload = build_payload()
    start = time.perf_counter()
    try:
        resp = await client.post(url, json=payload)
        elapsed = time.perf_counter() - start
        return {
            "index": index,
            "status": resp.status_code,
            "elapsed_ms": round(elapsed * 1000, 1),
            "body": resp.json(),
        }
    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "index": index,
            "status": 0,
            "elapsed_ms": round(elapsed * 1000, 1),
            "body": {"error": str(e)},
        }


async def run_test(concurrency: int, total: int, url: str) -> None:
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    timeout = httpx.Timeout(timeout=5, connect=10.0, read=30.0, write=10.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def limited(idx: int):
            async with semaphore:
                return await register_one(client, url, idx)

        print(f"\n开始并发测试: total={total}, concurrency={concurrency}, url={url}")
        print("-" * 60)

        start = time.perf_counter()
        tasks = [limited(i) for i in range(total)]
        results = await asyncio.gather(*tasks)
        wall_time = time.perf_counter() - start

    # 统计
    statuses: dict[int, int] = {}
    latencies: list[float] = []
    for r in results:
        statuses[r["status"]] = statuses.get(r["status"], 0) + 1
        latencies.append(r["elapsed_ms"])

    print(f"\n总耗时: {wall_time:.2f}s")
    print(f"吞吐量: {total / wall_time:.1f} req/s")
    print("\n状态码分布:")
    for code, count in sorted(statuses.items()):
        label = {200: "成功", 201: "创建成功", 409: "用户已存在", 429: "限流", 422: "参数错误", 0: "请求失败"}.get(
            code, "其他"
        )
        print(f"  {code} ({label}): {count}")

    latencies.sort()
    print("\n延迟统计 (ms):")
    print(f"  min:    {latencies[0]:.1f}")
    print(f"  p50:    {latencies[len(latencies) // 2]:.1f}")
    print(f"  p99:    {latencies[int(len(latencies) * 0.99)]:.1f}")
    print(f"  max:    {latencies[-1]:.1f}")

    # 打印前 5 个失败的请求
    failures = [r for r in results if r["status"] not in (201, 200)]
    if failures:
        print("\n失败请求示例 (前 5 个):")
        for r in failures[:5]:
            print(f"  [{r['index']}] status={r['status']} {r['elapsed_ms']}ms {r['body']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="并发注册接口测试")
    parser.add_argument("--concurrency", type=int, default=20, help="最大并发数 (default: 20)")
    parser.add_argument("--total", type=int, default=100, help="总请求数 (default: 100)")
    parser.add_argument("--url", type=str, default=BASE_URL, help="注册接口地址")
    args = parser.parse_args()

    asyncio.run(run_test(args.concurrency, args.total, args.url))
