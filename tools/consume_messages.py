import argparse
import asyncio
import json
import math
import os
import random
import time
from typing import Dict, List, Optional, Tuple

import httpx


class _LatencyStats:
    def __init__(self, reservoir_size: int = 2048) -> None:
        self.n = 0
        self.min_v = float("inf")
        self.max_v = 0.0
        self.mean = 0.0
        self.m2 = 0.0
        self.k = reservoir_size
        self.sample: List[float] = []

    def add(self, v: float) -> None:
        self.n += 1
        if v < self.min_v:
            self.min_v = v
        if v > self.max_v:
            self.max_v = v
        delta = v - self.mean
        self.mean += delta / self.n
        delta2 = v - self.mean
        self.m2 += delta * delta2
        if len(self.sample) < self.k:
            self.sample.append(v)
        else:
            j = random.randrange(self.n)
            if j < self.k:
                self.sample[j] = v

    def _pct(self, p: float) -> float:
        if not self.sample:
            return 0.0
        data = sorted(self.sample)
        idx = min(len(data) - 1, max(0, int(round(p * (len(data) - 1)))))
        return data[idx]

    def summary_ms(self) -> Dict[str, float]:
        if self.n <= 1:
            std = 0.0
        else:
            std = math.sqrt(self.m2 / (self.n - 1))
        return {
            "count": float(self.n),
            "avg_ms": self.mean * 1000.0,
            "std_ms": std * 1000.0,
            "min_ms": (0.0 if self.min_v == float("inf") else self.min_v * 1000.0),
            "p50_ms": self._pct(0.50) * 1000.0,
            "p90_ms": self._pct(0.90) * 1000.0,
            "p99_ms": self._pct(0.99) * 1000.0,
            "max_ms": self.max_v * 1000.0,
        }


async def _get_page(client: httpx.AsyncClient, thread_id: str, limit: int, cursor: Optional[str]) -> Tuple[bool, int, int, Optional[str], float]:
    params = {"limit": str(limit)}
    if cursor:
        params["cursor"] = cursor
    try:
        start = time.perf_counter()
        r = await client.get(f"/threads/{thread_id}/messages", params=params)
        elapsed = time.perf_counter() - start
        if r.status_code != 200:
            return False, r.status_code, 0, None, elapsed
        data = r.json()
        items = data.get("items") or []
        next_cursor = data.get("next_cursor")
        return True, r.status_code, len(items), next_cursor, elapsed
    except Exception:
        return False, 599, 0, None, 0.0


async def _worker(
    name: int,
    q: "asyncio.Queue[str]",
    client: httpx.AsyncClient,
    limit: int,
    ok: List[int],
    fail: List[int],
    code_counts: Dict[str, int],
    items_count: List[int],
    lat_stats: _LatencyStats,
    ok_initial: List[int],
    ok_follow: List[int],
    fail_initial: List[int],
    fail_follow: List[int],
    req_total: List[int],
) -> None:
    while True:
        thread_id = await q.get()
        if thread_id is None:  # type: ignore
            q.task_done()
            break
        cursor: Optional[str] = None if random.random() < 0.7 else None
        success, code, got, next_cursor, elapsed = await _get_page(client, thread_id, limit, cursor)
        req_total[0] += 1
        code_counts[str(code)] = code_counts.get(str(code), 0) + 1
        if success:
            ok[0] += 1
            ok_initial[0] += 1
            items_count[0] += got
            if elapsed:
                lat_stats.add(elapsed)
            if random.random() < 0.3 and next_cursor:
                s2, c2, g2, _, elapsed2 = await _get_page(client, thread_id, limit, next_cursor)
                req_total[0] += 1
                code_counts[str(c2)] = code_counts.get(str(c2), 0) + 1
                if s2:
                    ok[0] += 1
                    ok_follow[0] += 1
                    items_count[0] += g2
                    if elapsed2:
                        lat_stats.add(elapsed2)
                else:
                    fail[0] += 1
                    fail_follow[0] += 1
        else:
            fail[0] += 1
            fail_initial[0] += 1
        q.task_done()


def _load_threads(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data]
        if isinstance(data, dict) and "threads" in data:
            return [str(x) for x in data["threads"]]
    except Exception:
        pass
    return []


async def run(base_url: str, threads_file: str, reads: int, concurrency: int, limit: int, timeout: float) -> None:
    base_url = base_url.rstrip("/")
    threads = _load_threads(threads_file)
    if not threads:
        print(f"warn: no threads loaded from {threads_file}. Provide --threads-file or run seed first.")
        return
    ok = [0]
    fail = [0]
    items_count = [0]
    code_counts: Dict[str, int] = {}
    ok_initial = [0]
    ok_follow = [0]
    fail_initial = [0]
    fail_follow = [0]
    req_total = [0]
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    timeout_cfg = httpx.Timeout(timeout, connect=5.0)
    lat_stats = _LatencyStats()
    async with httpx.AsyncClient(base_url=base_url, limits=limits, timeout=timeout_cfg, trust_env=False) as client:
        try:
            await client.get("/docs", timeout=httpx.Timeout(3.0, connect=1.0))
        except Exception:
            pass
        q: "asyncio.Queue[str]" = asyncio.Queue()
        for _ in range(reads):
            q.put_nowait(random.choice(threads))
        workers = [
            asyncio.create_task(
                _worker(
                    i,
                    q,
                    client,
                    limit,
                    ok,
                    fail,
                    code_counts,
                    items_count,
                    lat_stats,
                    ok_initial,
                    ok_follow,
                    fail_initial,
                    fail_follow,
                    req_total,
                )
            )
            for i in range(concurrency)
        ]

        start = time.time()

        async def reporter() -> None:
            while any(not w.done() for w in workers):
                done = ok[0] + fail[0]
                reads_done = ok_initial[0] + fail_initial[0]
                rate = done / max(1e-9, time.time() - start)
                pending = q.qsize()
                print(
                    f"reads={reads_done}/{reads} req={done} ok={ok[0]} fail={fail[0]} items={items_count[0]} pending={pending} rate={rate:.1f} rps",
                    flush=True,
                )
                await asyncio.sleep(1.0)

        rep_task = asyncio.create_task(reporter())
        for _ in range(concurrency):
            q.put_nowait(None)  # type: ignore
        await q.join()
        await asyncio.gather(*workers, return_exceptions=True)
        rep_task.cancel()
        elapsed = time.time() - start
        rate = (ok[0] + fail[0]) / max(1e-9, elapsed)
        success_rate = (ok[0] / max(1, (ok[0] + fail[0])) * 100.0)
        print(
            f"done reads={reads} req={req_total[0]} ok={ok[0]} (ok_initial={ok_initial[0]}, ok_followup={ok_follow[0]}) "
            f"fail={fail[0]} items={items_count[0]} elapsed={elapsed:.2f}s rate={rate:.1f} rps success_rate={success_rate:.1f}%"
        )
        if lat_stats.n:
            ls = lat_stats.summary_ms()
            print(
                "summary latency_ms="
                f"avg={ls['avg_ms']:.1f} p50={ls['p50_ms']:.1f} p90={ls['p90_ms']:.1f} p99={ls['p99_ms']:.1f} "
                f"min={ls['min_ms']:.1f} max={ls['max_ms']:.1f} std={ls['std_ms']:.1f}"
            )
        if ok[0]:
            print(f"summary items_per_read avg={(items_count[0]/ok[0]):.2f}")
        if code_counts:
            top = sorted(code_counts.items(), key=lambda kv: int(kv[0]))
            dist = ", ".join([f"{k}:{v}" for k, v in top])
            print(f"summary codes={{ {dist} }}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default=os.getenv("CONSUME_BASE_URL", "http://127.0.0.1:3000"))
    p.add_argument("--threads-file", default=os.getenv("CONSUME_THREADS_FILE", "seed_threads.json"))
    p.add_argument("--reads", type=int, default=int(os.getenv("CONSUME_READS", "1000")))
    p.add_argument("--concurrency", type=int, default=int(os.getenv("CONSUME_CONCURRENCY", "50")))
    p.add_argument("--limit", type=int, default=int(os.getenv("CONSUME_LIMIT", "50")))
    p.add_argument("--timeout", type=float, default=float(os.getenv("CONSUME_TIMEOUT", "10")))
    args = p.parse_args()
    asyncio.run(run(args.base_url, args.threads_file, args.reads, args.concurrency, args.limit, args.timeout))


if __name__ == "__main__":
    main()
