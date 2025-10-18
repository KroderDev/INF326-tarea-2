import argparse
import asyncio
import json
import math
import os
import random
import time
import uuid
from typing import Dict, List, Tuple

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


def _rand_type() -> str:
    r = random.random()
    if r < 0.8:
        return "text"
    if r < 0.9:
        return "audio"
    return "file"


def _payload(thread_idx: int, msg_idx: int) -> dict:
    t = _rand_type()
    now = int(time.time() * 1000)
    rid = random.randint(1, 1_000_000_000)
    p = [f"/files/{random.randint(1, 1000)}.bin"] if t != "text" else [f"/notes/{random.randint(1, 1000)}.txt"]
    return {"content": f"msg {now}-{rid} t{thread_idx} #{msg_idx}", "type": t, "paths": p}


async def _post_with_retry(client: httpx.AsyncClient, url: str, user_id: str, data: dict, attempts: int = 5) -> Tuple[bool, int, int, float]:
    delay = 0.2
    start = time.perf_counter()
    tried = 0
    for i in range(attempts):
        tried += 1
        try:
            r = await client.post(url, headers={"X-User-Id": user_id}, json=data)
            if r.status_code == 201:
                return True, r.status_code, tried, time.perf_counter() - start
            if r.status_code in {429, 500, 502, 503, 504}:
                await asyncio.sleep(delay + random.random() * 0.2)
                delay *= 2
                continue
            return False, r.status_code, tried, time.perf_counter() - start
        except Exception:
            await asyncio.sleep(delay + random.random() * 0.2)
            delay *= 2
    return False, 599, tried, time.perf_counter() - start


async def _worker(
    name: int,
    q: "asyncio.Queue[Tuple[int, str, str]]",
    client: httpx.AsyncClient,
    ok: List[int],
    fail: List[int],
    code_counts: Dict[str, int],
    lat_stats: _LatencyStats,
    attempts_sum: List[int],
    attempts_max: List[int],
    attempts_multi: List[int],
) -> None:
    while True:
        item = await q.get()
        if item is None:  # type: ignore
            q.task_done()
            break
        thread_idx, thread_id, user_id = item
        url = f"/threads/{thread_id}/messages"
        data = _payload(thread_idx, ok[0] + fail[0] + 1)
        success, code, tries, elapsed = await _post_with_retry(client, url, user_id, data)
        code_counts[str(code)] = code_counts.get(str(code), 0) + 1
        lat_stats.add(elapsed)
        attempts_sum[0] += tries
        if tries > attempts_max[0]:
            attempts_max[0] = tries
        if tries > 1:
            attempts_multi[0] += 1
        if success:
            ok[0] += 1
        else:
            fail[0] += 1
        q.task_done()


async def run(base_url: str, threads: int, messages: int, users: int, concurrency: int, timeout: float, threads_out: str | None) -> None:
    base_url = base_url.rstrip("/")
    user_ids = [str(uuid.uuid4()) for _ in range(users)]
    thread_ids = [str(uuid.uuid4()) for _ in range(threads)]
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
    timeout_cfg = httpx.Timeout(timeout, connect=5.0)
    ok = [0]
    fail = [0]
    code_counts: Dict[str, int] = {}
    lat_stats = _LatencyStats()
    attempts_sum = [0]
    attempts_max = [1]
    attempts_multi = [0]
    total = threads * messages

    async with httpx.AsyncClient(base_url=base_url, limits=limits, timeout=timeout_cfg, trust_env=False) as client:
        try:
            await client.get("/docs", timeout=httpx.Timeout(3.0, connect=1.0))
        except Exception:
            pass
        q: "asyncio.Queue[Tuple[int, str, str]]" = asyncio.Queue()
        for idx, tid in enumerate(thread_ids):
            for _ in range(messages):
                q.put_nowait((idx, tid, random.choice(user_ids)))

        workers = [
            asyncio.create_task(
                _worker(
                    i, q, client, ok, fail, code_counts, lat_stats, attempts_sum, attempts_max, attempts_multi
                )
            )
            for i in range(concurrency)
        ]

        start = time.time()

        async def reporter() -> None:
            warned = False
            while any(not w.done() for w in workers):
                done = ok[0] + fail[0]
                rate = done / max(1e-9, time.time() - start)
                pending = q.qsize()
                print(
                    f"sent={done}/{total} ok={ok[0]} fail={fail[0]} pending={pending} rate={rate:.1f} rps",
                    flush=True,
                )
                if not warned and time.time() - start > 5 and done == 0:
                    print(
                        "No progress yet. Verify BASE_URL is reachable (try http://127.0.0.1:3000 or http://host.docker.internal:3000) and the API is up.",
                        flush=True,
                    )
                    warned = True
                await asyncio.sleep(1.0)

        rep_task = asyncio.create_task(reporter())

        for _ in range(concurrency):
            q.put_nowait(None)  # type: ignore
        await q.join()
        await asyncio.gather(*workers, return_exceptions=True)
        rep_task.cancel()
        elapsed = time.time() - start
        rate = (ok[0] + fail[0]) / max(1e-9, elapsed)
        print(f"done total={total} ok={ok[0]} fail={fail[0]} elapsed={elapsed:.2f}s rate={rate:.1f} rps", flush=True)
        success_rate = (ok[0] / total * 100.0) if total else 0.0
        print("summary:")
        print(f"  base_url={base_url}")
        print(f"  threads={threads} messages_per_thread={messages} users={users} concurrency={concurrency}")
        print(f"  elapsed={elapsed:.2f}s throughput={rate:.1f} rps success={ok[0]} fail={fail[0]} success_rate={success_rate:.1f}%")
        if lat_stats.n:
            ls = lat_stats.summary_ms()
            print(
                "  latency_ms="
                f"avg={ls['avg_ms']:.1f} p50={ls['p50_ms']:.1f} p90={ls['p90_ms']:.1f} p99={ls['p99_ms']:.1f} "
                f"min={ls['min_ms']:.1f} max={ls['max_ms']:.1f} std={ls['std_ms']:.1f}"
            )
            avg_attempts = attempts_sum[0] / max(1, (ok[0] + fail[0]))
            multi_ratio = attempts_multi[0] / max(1, (ok[0] + fail[0])) * 100.0
            print(
                f"  attempts avg={avg_attempts:.2f} max={attempts_max[0]} multi_attempts={attempts_multi[0]} ({multi_ratio:.1f}%)"
            )
        if code_counts:
            top = sorted(code_counts.items(), key=lambda kv: int(kv[0]))
            dist = ", ".join([f"{k}:{v}" for k, v in top])
            print(f"  codes={{ {dist} }}")
        if threads_out:
            try:
                with open(threads_out, "w", encoding="utf-8") as f:
                    json.dump({
                        "base_url": base_url,
                        "threads": thread_ids,
                        "users": user_ids,
                        "total_messages": total,
                        "threads_count": len(thread_ids),
                        "created_at": int(time.time()),
                    }, f)
                print(f"  threads_file={threads_out}")
            except Exception as e:
                print(f"  warn: could not write threads file '{threads_out}': {e}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default=os.getenv("SEED_BASE_URL", "http://localhost:3000"))
    p.add_argument("--threads", type=int, default=int(os.getenv("SEED_THREADS", "10")))
    p.add_argument("--messages", type=int, default=int(os.getenv("SEED_MESSAGES", "500")))
    p.add_argument("--users", type=int, default=int(os.getenv("SEED_USERS", "10")))
    p.add_argument("--concurrency", type=int, default=int(os.getenv("SEED_CONCURRENCY", "100")))
    p.add_argument("--timeout", type=float, default=float(os.getenv("SEED_TIMEOUT", "10")))
    p.add_argument("--threads-out", default=os.getenv("SEED_THREADS_OUT", "seed_threads.json"))
    args = p.parse_args()
    asyncio.run(run(args.base_url, args.threads, args.messages, args.users, args.concurrency, args.timeout, args.threads_out))


if __name__ == "__main__":
    main()
